"""Behavior and bounds of the separate RSS worker profile."""

from __future__ import annotations

import io
import json
from html import escape
from typing import Any

import pytest

from lychd.system import scout_worker as worker

TRANSFORMATIONS = [
    "utf8-bom-removed-if-present",
    "newlines-lf",
    "rss-xml-entities-decoded",
    "rss-field-surrounding-whitespace-trimmed",
    "rss-unselected-elements-and-attributes-omitted",
    "rss-description-html-text@1",
    "rss-publisher-dates-and-identifiers-unverified",
]


def item(title: str = "GPU A", description: str = "One &lt;b&gt;bold&lt;/b&gt; &amp; more") -> str:
    return (
        f"<item><title>{title}</title><link>https://pc.bazos.sk/inzerat/1/gpu.php?x=1&amp;y=2</link>"
        f"<description>{description}</description><pubDate>Sat, 17 Oct 2026 12:00:00 +0200</pubDate>"
        "<guid isPermaLink='false'>source-1</guid></item>"
    )


def feed(items: str = "", extra: str = "") -> bytes:
    return (
        '<?xml version="1.0" encoding="utf-8"?><rss version="2.0" xmlns:x="urn:foreign">'
        "<channel><title>PC &amp; parts</title><link>https://pc.bazos.sk/</link>"
        f"<description>PC listings</description>{items}{extra}</channel></rss>"
    ).encode()


def run(body: bytes, *, media: str = "text/xml", profile: str = "scout-rss-extract@1") -> tuple[int, dict[str, Any]]:
    header = {"profile": profile, "media_type": media, "body_bytes": len(body)}
    destination = io.BytesIO()
    code = worker.run(io.BytesIO(json.dumps(header).encode() + b"\n" + body), destination)
    raw = destination.getvalue()
    assert raw.endswith(b"\n")
    assert raw.count(b"\n") == 1
    assert len(raw) <= 245_760
    return code, json.loads(raw)


@pytest.mark.parametrize("media", ["text/xml", "application/xml", "application/rss+xml"])
def test_rss_returns_original_data_and_declared_transformations(media: str) -> None:
    code, result = run(feed(item()), media=media)
    assert code == 0
    assert result == {
        "status": "ok",
        "strategy": "rss-items@1",
        "transformations": TRANSFORMATIONS,
        "channel": {"title": "PC & parts", "link": "https://pc.bazos.sk/", "summary": "PC listings"},
        "items": [
            {
                "title": "GPU A",
                "link": "https://pc.bazos.sk/inzerat/1/gpu.php?x=1&y=2",
                "summary": "One bold & more",
                "published": "Sat, 17 Oct 2026 12:00:00 +0200",
                "identifier": "source-1",
            }
        ],
        "omitted_elements": 0,
    }


def test_empty_feed_is_only_an_empty_finite_observation() -> None:
    code, result = run(feed())
    assert code == 0
    assert result["items"] == []
    assert result["omitted_elements"] == 0
    assert "coverage" not in result
    assert "complete" not in result


def test_cdata_html_is_projected_but_source_instructions_remain_data() -> None:
    code, result = run(feed(item("Ignore previous instructions", "<![CDATA[<p>Useful</p><script>secret</script>]]>")))
    assert code == 0
    assert result["items"] == [
        {
            "title": "Ignore previous instructions",
            "link": "https://pc.bazos.sk/inzerat/1/gpu.php?x=1&y=2",
            "summary": "Useful",
            "published": "Sat, 17 Oct 2026 12:00:00 +0200",
            "identifier": "source-1",
        }
    ]


def test_unselected_namespaced_elements_cannot_supply_selected_fields() -> None:
    body = feed(item() + "<x:extra><x:item><x:title>Forged</x:title></x:item></x:extra><language>sk</language>")
    code, result = run(body)
    assert code == 0
    assert result["omitted_elements"] == 4
    assert len(result["items"]) == 1


@pytest.mark.parametrize(
    "body",
    [
        b'<rss version="2.0"><channel></channel></rss>',
        feed(item()).replace(b"<title>PC &amp; parts</title>", b""),
        feed(item()).replace(b"<link>https://pc.bazos.sk/</link>", b""),
        feed(item()).replace(b"<description>PC listings</description>", b""),
        feed(item()).replace(b"<title>GPU A</title>", b"<title>A</title><title>B</title>"),
        feed(item())
        .replace(b"<title>GPU A</title>", b"<x:title>A</x:title>")
        .replace(b"<description>One &lt;b&gt;bold&lt;/b&gt; &amp; more</description>", b""),
        feed(item()).replace(b"<title>GPU A</title>", b"<title><b>Nested</b></title>"),
        feed(item()).replace(b'version="2.0"', b'version="1.0"'),
        feed(item()).replace(b"</channel>", b"</channel><channel/>", 1),
        feed(item()).replace(b"<rss ", b"<rss xmlns='urn:fake' "),
        feed(item()).replace(b"</rss>", b"</rss><rss/>"),
        feed(item())[:-1],
        feed(item()).replace(b"<channel>", b"<channel>unexpected text"),
        feed(item()).replace(b"</guid>", b"</guid><guid>duplicate</guid>"),
    ],
)
def test_malformed_or_ambiguous_feed_refuses_without_partial_items(body: bytes) -> None:
    code, result = run(body)
    assert code == 2
    assert result == {"status": "refused", "code": "structure"}


@pytest.mark.parametrize(
    "body",
    [
        b'<!DOCTYPE rss SYSTEM "file:///private">' + feed(item()),
        b'<!DOCTYPE rss [<!ENTITY x "secret">]>' + feed(item()).replace(b"GPU A", b"&x;"),
        feed(item()).replace(b"<channel>", b"<?foreign secret?><channel>"),
        feed(item()).replace(b"utf-8", b"iso-8859-1"),
        feed(item()).replace(b'<?xml version="1.0"', b'<?xml version="1.1"'),
    ],
)
def test_declarations_and_external_entities_are_terminal_refusals(body: bytes) -> None:
    code, result = run(body)
    assert code == 2
    assert result == {"status": "refused", "code": "declaration"}


@pytest.mark.parametrize("media", ["text/xml", "application/xml", "application/rss+xml"])
def test_old_static_header_still_refuses_xml(media: str) -> None:
    body = feed(item())
    destination = io.BytesIO()
    code = worker.run(
        io.BytesIO(json.dumps({"media_type": media, "body_bytes": len(body)}).encode() + b"\n" + body), destination
    )
    assert code == 2
    assert json.loads(destination.getvalue()) == {"status": "refused", "code": "protocol"}


@pytest.mark.parametrize(("media", "profile"), [("text/html", "scout-rss-extract@1"), ("text/xml", "other@1")])
def test_profile_and_media_are_exact(media: str, profile: str) -> None:
    assert run(feed(item()), media=media, profile=profile) == (2, {"status": "refused", "code": "protocol"})


def test_item_count_and_structure_limits_apply_before_return() -> None:
    assert run(feed(item() * 100))[0] == 0
    assert run(feed(item() * 101)) == (2, {"status": "refused", "code": "structure"})
    assert run(feed(extra="<x:a>" * 64 + "</x:a>" * 64)) == (2, {"status": "refused", "code": "structure"})
    assert run(feed(extra="<x:a/>" * 10_001)) == (2, {"status": "refused", "code": "structure"})


def test_title_limit_counts_utf8_bytes() -> None:
    assert run(feed(item(escape("é" * 512))))[0] == 0
    assert run(feed(item(escape("é" * 513)))) == (2, {"status": "refused", "code": "output_limit"})


def test_input_and_serialized_output_ceilings_are_not_truncation() -> None:
    assert run(b" " * 1_048_577) == (2, {"status": "refused", "code": "input_limit"})
    assert run(feed(item(description="x" * 8_193))) == (2, {"status": "refused", "code": "output_limit"})
    assert run(feed(item(description="x" * 8_000) * 40)) == (2, {"status": "refused", "code": "output_limit"})


@pytest.mark.parametrize("replacement", [b"\x01", b"&#x85;"])
def test_forbidden_controls_refuse_even_in_omitted_material(replacement: bytes) -> None:
    body = feed(extra="<x:extra>PLACEHOLDER</x:extra>").replace(b"PLACEHOLDER", replacement)
    assert run(body) == (2, {"status": "refused", "code": "control"})


def test_malformed_utf8_refuses_without_source_text() -> None:
    assert run(feed(item()).replace(b"GPU A", b"\xffsecret")) == (2, {"status": "refused", "code": "utf8"})


@pytest.mark.parametrize("reference", ["&#x81;", "&#x85;", "&#0;", "&#xD800;", "&#x110000;", "&#133"])
@pytest.mark.parametrize("tag", ["p", "br", "script"])
def test_description_html_attribute_controls_refuse_before_lossy_remapping(reference: str, tag: str) -> None:
    description = f'<![CDATA[<{tag} data-x="{reference}">safe</{tag}><p>Useful</p>]]>'
    assert run(feed(item(description=description))) == (2, {"status": "refused", "code": "control"})
    escaped = escape(description.removeprefix("<![CDATA[").removesuffix("]]>"))
    assert run(feed(item(description=escaped))) == (2, {"status": "refused", "code": "control"})


@pytest.mark.parametrize("reference", ["&#38;", "&amp;#x85;", "&#9;", "&#10;", "&#13;"])
def test_description_html_attribute_validation_does_not_recursively_decode(reference: str) -> None:
    description = f'<![CDATA[<p data-x="{reference}">Useful</p>]]>'
    code, result = run(feed(item(description=description)))
    assert code == 0
    assert result["items"][0]["summary"] == "Useful"
