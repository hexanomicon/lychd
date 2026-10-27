from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import pytest
from scripts.reach_prepare import installation_url, load_policy, main

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / "examples" / "reach"


def test_public_template_validates_and_install_url_has_no_admin_scope(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--policy", str(EXAMPLES / "policy.toml"), "--install-url"]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "configuration_valid"
    assert output["preparation_only"] is True
    assert output["delivery"] == "not_attempted"
    install_url = output["install_url"]
    assert isinstance(install_url, str)
    query = parse_qs(urlsplit(install_url).query)
    assert query["permissions"] == ["3072"]
    assert set(query["scope"][0].split()) == {"bot", "applications.commands"}


def test_history_permission_is_explicit_and_still_not_admin() -> None:
    policy = load_policy(EXAMPLES / "policy.toml")
    policy = type(policy).model_validate({**policy.model_dump(), "context_message_limit": 20})
    permissions = int(parse_qs(urlsplit(installation_url(policy)).query)["permissions"][0])
    assert permissions == 3072 + (1 << 16)
    assert permissions & (1 << 3) == 0


def test_event_preview_is_content_free(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    event = json.loads((EXAMPLES / "event.json").read_text())
    event["occurred_at"] = datetime.now(UTC).isoformat()
    event["question"] = "private-synthetic-question"
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event))
    assert main(["--policy", str(EXAMPLES / "policy.toml"), "--event", str(path)]) == 0
    output = capsys.readouterr().out
    assert json.loads(output)["status"] == "eligible"
    assert "private-synthetic-question" not in output


def test_old_event_is_refused_with_no_question_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    event = json.loads((EXAMPLES / "event.json").read_text())
    event["occurred_at"] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    path = tmp_path / "event.json"
    path.write_text(json.dumps(event))
    assert main(["--policy", str(EXAMPLES / "policy.toml"), "--event", str(path)]) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "refused"
    assert output["delivery"] == "not_attempted"


@pytest.mark.parametrize("kind", ["unknown_secret_field", "too_large", "missing", "bad_toml"])
def test_bad_policy_diagnostics_never_echo_input(kind: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "policy.toml"
    if kind == "unknown_secret_field":
        path.write_text('bot_token = "synthetic-secret"\n' + (EXAMPLES / "policy.toml").read_text())
    elif kind == "too_large":
        path.write_text("synthetic-secret" * 6000)
    elif kind == "bad_toml":
        path.write_text('bot_token = "synthetic-secret')
    assert main(["--policy", str(path)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "synthetic-secret" not in captured.err
    assert "Invalid or unreadable" in captured.err


def test_duplicate_json_keys_are_refused(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = tmp_path / "event.json"
    path.write_text('{"question":"synthetic-secret", "question":"other"}')
    assert main(["--policy", str(EXAMPLES / "policy.toml"), "--event", str(path)]) == 1
    assert "synthetic-secret" not in capsys.readouterr().err
