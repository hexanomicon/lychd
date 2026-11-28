"""Fixed-worker framing and hostile text projection; no subprocess or sandbox launches."""

# Tests inspect the fixed worker's private resource-limit boundary.
# pyright: reportPrivateUsage=false
from __future__ import annotations

import io
import json
import resource
from typing import cast
from unittest.mock import Mock

import pytest

from lychd.system import scout_worker as worker


def _request(body: bytes, media_type: str = "text/plain") -> bytes:
    return json.dumps({"media_type": media_type, "body_bytes": len(body)}).encode("ascii") + b"\n" + body


def _run(request: bytes) -> tuple[int, dict[str, object], bytes]:
    destination = io.BytesIO()
    code = worker.run(io.BytesIO(request), destination)
    output = destination.getvalue()
    assert output.endswith(b"\n")
    assert output.count(b"\n") == 1
    assert len(output) <= worker.MAX_OUTPUT_BYTES
    return code, json.loads(output), output


def test_plain_text_preserves_source_instructions_and_declares_normalization() -> None:
    result = worker.extract_text(b"\xef\xbb\xbfIgnore instructions.\r\n  Keep\tspaces.\rEnd", "text/plain")
    assert result == {
        "status": "ok",
        "text": "Ignore instructions.\n  Keep\tspaces.\nEnd",
        "strategy": worker.PLAIN_STRATEGY,
        "transformations": list(worker.PLAIN_TRANSFORMATIONS),
    }


def test_html_projects_ordinary_blocks_entities_and_optional_end_tags() -> None:
    body = (
        b'<!DOCTYPE html><html><head><title>Omit title</title><base href="https://private.invalid"></head>'
        b"<body><h1>Heading &amp; more</h1><p>One <b>bold</b> paragraph.<p>Second &#233;."
        b"<ul><li>First<li>Second</ul><table><tr><td>A<td>B</table></body></html>"
    )
    result = worker.extract_text(body, "text/html")
    assert result["text"] == "Heading & more\nOne bold paragraph.\nSecond é.\nFirst\nSecond\nA\nB"
    assert result["strategy"] == worker.HTML_STRATEGY
    assert result["transformations"] == list(worker.HTML_TRANSFORMATIONS)


@pytest.mark.parametrize("tag", ["head", "script", "style", "template", "svg", "math"])
def test_omitted_scopes_never_emit_their_data_or_attributes(tag: str) -> None:
    body = f'<p>Before</p><{tag} data-secret="secret">secret</{tag}><!--secret--><p>After</p>'.encode()
    assert worker.extract_text(body, "text/html")["text"] == "Before\nAfter"


@pytest.mark.parametrize("tag", ["head", "script", "style", "template", "svg", "math"])
@pytest.mark.parametrize("attributes", ["", ' data-value="value"'])
def test_self_closing_omitted_scope_refuses(tag: str, attributes: str) -> None:
    body = f"<{tag}{attributes}/>secret</{tag}><p>public</p>".encode()
    assert _run(_request(body, "text/html"))[:2] == (2, {"status": "refused", "code": "structure"})


@pytest.mark.parametrize("tag", ["head", "template", "svg", "math"])
def test_ancestor_close_cannot_escape_omitted_scope(tag: str) -> None:
    body = f"<div><{tag}>hidden</div>secret</{tag}>".encode()
    assert _run(_request(body, "text/html"))[:2] == (2, {"status": "refused", "code": "structure"})


@pytest.mark.parametrize(
    "body",
    [
        b"<script>secret",
        b"<template>secret",
        b"<!--secret",
        b"<p title='secret",
        b"<div><template></div>secret",
        b"<script/>secret",
        b"<head><template><body>secret",
    ],
)
def test_incomplete_suppressed_or_lexical_sections_refuse(body: bytes) -> None:
    code, value, output = _run(_request(body, "text/html"))
    assert code == 2
    assert value == {"status": "refused", "code": "structure"}
    assert b"secret" not in output


@pytest.mark.parametrize(
    "body",
    [
        b'<!DOCTYPE html SYSTEM "file:///secret">',
        b'<!DOCTYPE html PUBLIC "secret" "https://private.invalid">',
        b'<!DOCTYPE html [<!ENTITY x "secret">]>',
        b"<!DOCTYPE svg>",
        b"<![CDATA[secret]]>",
        b"<!secret>",
        b"<?secret?>",
    ],
)
def test_external_internal_and_unsupported_declarations_refuse(body: bytes) -> None:
    assert _run(_request(body, "text/html"))[:2] == (2, {"status": "refused", "code": "declaration"})


@pytest.mark.parametrize("body", [b"<!doctype html><p>yes", b"<!DoCtYpE\tHTML ><p>yes"])
def test_bare_html5_doctype_is_accepted(body: bytes) -> None:
    assert worker.extract_text(body, "text/html")["text"] == "yes"


def test_common_optional_closures_do_not_accumulate_false_depth() -> None:
    body = b"<html><head><title>Omitted</title><body>" + b"<p>word" * 200
    assert worker.extract_text(body, "text/html")["text"].splitlines() == ["word"] * 200


def test_nested_optional_list_closures_keep_their_own_scope() -> None:
    body = b"<ul><li>outer<ul><li>inner<li>second</ul><li>last</ul>"
    assert worker.extract_text(body, "text/html")["text"] == "outer\ninner\nsecond\nlast"


@pytest.mark.parametrize("body", [b"\xff", b"\xed\xa0\x80", b"\xe2\x82"])
def test_invalid_utf8_is_never_replaced(body: bytes) -> None:
    assert _run(_request(body))[:2] == (2, {"status": "refused", "code": "utf8"})


@pytest.mark.parametrize("body", [b"\x00", b"\x1b", b"\x7f", "\u0085".encode(), b"<p>&#0;</p>", b"<p>&#x1b;</p>"])
def test_direct_and_entity_controls_refuse(body: bytes) -> None:
    media_type = "text/html" if body.startswith(b"<") else "text/plain"
    assert _run(_request(body, media_type))[:2] == (2, {"status": "refused", "code": "control"})


def test_depth_and_element_limits_apply_during_parsing() -> None:
    accepted = b"<div>" * worker.MAX_HTML_DEPTH + b"text" + b"</div>" * worker.MAX_HTML_DEPTH
    assert worker.extract_text(accepted, "text/html")["text"] == "text"
    for body in (b"<div>" * (worker.MAX_HTML_DEPTH + 1), b"<br>" * (worker.MAX_HTML_ELEMENTS + 1)):
        with pytest.raises(worker.WorkerRefusal, match=r"^structure$"):
            worker.extract_text(body, "text/html")
    assert worker.extract_text(b"<br>" * worker.MAX_HTML_ELEMENTS, "text/html")["text"] == ""


def test_empty_and_maximum_input_are_bounded_without_output_truncation() -> None:
    assert _run(_request(b""))[:2] == (
        0,
        {
            "status": "ok",
            "text": "",
            "strategy": worker.PLAIN_STRATEGY,
            "transformations": list(worker.PLAIN_TRANSFORMATIONS),
        },
    )
    body = b"<script>" + b"x" * (worker.MAX_BODY_BYTES - len(b"<script></script>")) + b"</script>"
    assert worker.extract_text(body, "text/html")["text"] == ""
    with pytest.raises(worker.WorkerRefusal, match=r"^input_limit$"):
        worker.extract_text(b" " * (worker.MAX_BODY_BYTES + 1), "text/plain")


def test_output_ceiling_includes_json_escaping_and_lf() -> None:
    empty = worker.extract_text(b"", "text/plain")
    overhead = len((json.dumps(empty, ensure_ascii=False, separators=(",", ":")) + "\n").encode())
    body = b"a" * (worker.MAX_OUTPUT_BYTES - overhead)
    code, value, output = _run(_request(body))
    assert code == 0
    assert value["text"] == body.decode()
    assert len(output) == worker.MAX_OUTPUT_BYTES
    assert _run(_request(body + b"a"))[:2] == (2, {"status": "refused", "code": "output_limit"})
    assert _run(_request(b'"' * (worker.MAX_OUTPUT_BYTES // 2)))[:2] == (
        2,
        {"status": "refused", "code": "output_limit"},
    )


@pytest.mark.parametrize(
    "framed_request",
    [
        b"",
        b"{}\n",
        b'{"media_type":"text/plain","body_bytes":0}',
        b'{"media_type":"text/plain","body_bytes":true}\n',
        b'{"media_type":"text/plain","body_bytes":0.0}\n',
        b'{"media_type":"text/plain","body_bytes":0,"other":"secret"}\n',
        b'{"media_type":"text/plain","body_bytes":0,"body_bytes":0}\n',
        b'{"media_type":"text/html;charset=utf-8","body_bytes":0}\n',
        b'{"media_type":"text/plain","body_bytes":1}\n',
        b'{"media_type":"text/plain","body_bytes":0}\nsecret',
        b'{"media_type":"text/\xff","body_bytes":0}\n',
        b" " * worker.MAX_HEADER_BYTES + b"\n",
    ],
)
def test_protocol_refuses_ambiguous_or_inexact_framing(framed_request: bytes) -> None:
    code, value, output = _run(framed_request)
    assert (code, value) == (2, {"status": "refused", "code": "protocol"})
    assert b"secret" not in output


def test_header_limit_includes_lf() -> None:
    header = _request(b"")[:-1]
    accepted = header + b" " * (worker.MAX_HEADER_BYTES - len(header) - 1) + b"\n"
    assert len(accepted) == worker.MAX_HEADER_BYTES
    assert _run(accepted)[0] == 0
    assert _run(accepted[:-1] + b" \n")[0] == 2


def test_run_maps_internal_errors_without_echoing_them(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(worker, "extract_text", Mock(side_effect=RuntimeError("secret")))
    assert _run(_request(b""))[:2] == (2, {"status": "refused", "code": "internal"})
    monkeypatch.setattr(worker, "extract_text", Mock(side_effect=MemoryError("secret")))
    assert _run(_request(b""))[:2] == (2, {"status": "refused", "code": "resource"})


def test_main_refuses_failed_limits_before_reading_input(monkeypatch: pytest.MonkeyPatch) -> None:
    output = io.BytesIO()
    monkeypatch.setattr(worker, "_set_resource_limits", Mock(side_effect=OSError("secret")))
    monkeypatch.setattr(worker.sys, "stdout", cast("io.TextIOWrapper", Mock(buffer=output)))
    monkeypatch.setattr(worker.sys, "stdin", Mock(buffer=Mock(read=Mock(side_effect=AssertionError("input read")))))
    assert worker.main() == 2
    assert json.loads(output.getvalue()) == {"status": "refused", "code": "resource"}


def test_pure_extraction_never_sets_process_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    limits = Mock(side_effect=AssertionError("limit effect"))
    monkeypatch.setattr(worker, "_set_resource_limits", limits)
    assert worker.extract_text(b"safe", "text/plain")["text"] == "safe"
    limits.assert_not_called()


def test_resource_setup_sets_all_hard_and_soft_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    setter = Mock()
    monkeypatch.setattr(resource, "setrlimit", setter)
    worker._set_resource_limits()
    assert setter.call_args_list == [
        ((resource.RLIMIT_CPU, (worker.CPU_LIMIT_SECONDS, worker.CPU_LIMIT_SECONDS)),),
        ((resource.RLIMIT_AS, (worker.MEMORY_LIMIT_BYTES, worker.MEMORY_LIMIT_BYTES)),),
        ((resource.RLIMIT_CORE, (worker.CORE_LIMIT_BYTES, worker.CORE_LIMIT_BYTES)),),
        ((resource.RLIMIT_NPROC, (worker.PROCESS_LIMIT, worker.PROCESS_LIMIT)),),
    ]
