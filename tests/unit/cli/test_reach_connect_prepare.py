"""The operator preview prepares all destinations without exposing content by default."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from scripts.reach_connect_prepare import main

EXAMPLES = Path(__file__).resolve().parents[3] / "examples" / "reach" / "connected"


def test_wuphf_preview_is_inert_and_content_free(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--policy", str(EXAMPLES / "policy.json"), "--requests", str(EXAMPLES / "wuphf.json")]) == 0
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["count"] == 3
    assert result["profile"] == "reach.connect.prepare@1"
    assert result["delivery"] == "not_attempted"
    assert "client@example.net" not in captured.out
    assert "accepted release" not in captured.out
    assert "batch" not in result
    assert captured.err == ""


def test_explicit_payload_preview_retains_each_provider(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            ["--policy", str(EXAMPLES / "policy.json"), "--requests", str(EXAMPLES / "wuphf.json"), "--include-payload"]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert [item["preparation"]["connection"]["provider"] for item in result["requests"]] == [
        "gmail",
        "telegram",
        "github",
    ]
    assert "release candidate" in result["requests"][1]["body"]


def test_founder_launch_prepares_mail_and_organic_posts(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "--policy",
                str(EXAMPLES / "founder-policy.json"),
                "--requests",
                str(EXAMPLES / "founder-launch.json"),
                "--include-payload",
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["delivery"] == "not_attempted"
    assert [item["preparation"]["connection"]["provider"] for item in result["requests"]] == [
        "fastmail",
        "facebook",
        "linkedin",
        "x",
    ]
    linkedin = json.loads(result["requests"][2]["body"])
    assert linkedin["author"] == "urn:li:person:example-member"
    assert linkedin["visibility"] == "PUBLIC"
    assert json.loads(result["requests"][3]["body"])["made_with_ai"] is True


@pytest.mark.parametrize("kind", ["duplicate", "unknown_secret", "oversized", "missing", "bad_target"])
def test_failure_emits_no_partial_plan_or_input(kind: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    request_path = tmp_path / "request.json"
    if kind == "duplicate":
        request_path.write_text('{"requests": [], "requests": "synthetic-secret"}')
    elif kind == "unknown_secret":
        request_path.write_text('{"requests": [], "token": "synthetic-secret"}')
    elif kind == "oversized":
        request_path.write_text("synthetic-secret" * 20_000)
    elif kind == "bad_target":
        document = json.loads((EXAMPLES / "wuphf.json").read_text())
        document["requests"][-1]["target"]["issue_number"] = 99
        document["requests"][0]["text"] = "synthetic-secret"
        request_path.write_text(json.dumps(document))
    assert main(["--policy", str(EXAMPLES / "policy.json"), "--requests", str(request_path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "synthetic-secret" not in captured.err
    assert "Invalid or unsupported" in captured.err
