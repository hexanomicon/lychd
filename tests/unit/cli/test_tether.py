"""Native CLI dispatch and original-profile selection boundaries."""

# pyright: reportPrivateUsage=false

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from lychd.cli.commands import _initial_profile
from lychd.cli.tether import tether_group
from lychd.config.settings import SettingsSnapshot


@pytest.mark.parametrize(
    ("arguments", "method"),
    [
        (["prepare", "--intent", "/public.json", "--dry-run"], "prepare"),
        (["bind", "--dry-run"], "bind"),
        (["activate", "--dry-run"], "activate"),
        (["inspect"], "inspect"),
        (["revoke", "--network", "network", "--generation", "generation", "--dry-run"], "revoke"),
        (["import-key", "--secret", "reference", "--file", "/private", "--dry-run"], "import_key"),
        (["runtime-dir"], "runtime_dir"),
        (["resume"], "resume"),
        (["admit", "--attachment", "road", "--generation", "2", "--dry-run"], "admit"),
    ],
)
def test_tether_commands_use_native_service_only(
    arguments: list[str], method: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    service = MagicMock()
    getattr(service, method).return_value = {"ok": True}
    monkeypatch.setattr("lychd.system.services.tether.service.NativeTetherService", lambda: service)
    result = CliRunner().invoke(tether_group, arguments)
    assert result.exit_code == 0, result.output
    assert result.output.strip() == '{"ok": true}'
    assert getattr(service, method).call_count == 1


def test_native_errors_do_not_render_private_values(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MagicMock()
    service.inspect.side_effect = ValueError("PRIVATE material")
    monkeypatch.setattr("lychd.system.services.tether.service.NativeTetherService", lambda: service)
    result = CliRunner().invoke(tether_group, ["inspect"])
    assert result.exit_code != 0
    assert "PRIVATE" not in result.output


def test_tether_profile_prepares_settings_without_mutating_cached_values(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = SettingsSnapshot(payload="{}").materialize()
    original = settings.model_dump()
    rune = object()
    assembly = object()
    monkeypatch.setattr(
        "lychd.system.services.tether.models.load_intent", lambda _path: SimpleNamespace(rune=rune, web_port=9123)
    )
    monkeypatch.setattr("lychd.extensions.host.assemble_extensions", lambda _prepared: assembly)
    prepared, runes, extensions = _initial_profile(settings, profile="tether-container-v1", intent=Path("/public.json"))
    assert settings.model_dump() == original
    assert prepared.server.port == 9123
    assert prepared.extensions.builtins == ("tether",)
    assert prepared.extensions.crypt == ()
    assert runes == (rune,)
    assert extensions is assembly


def test_ordinary_bind_keeps_native_helpers_and_attestor(monkeypatch: pytest.MonkeyPatch) -> None:
    from lychd.cli.binding import BindingCommandSession
    from lychd.system.services.bind import BindRequest

    settings = SettingsSnapshot(payload="{}").materialize()
    settings.extensions.builtins = ("tether",)
    native = MagicMock()
    request = BindRequest.compile(
        manifests=(),
        plain_units={"lychd-tether-runtime.service": "owned runtime helper"},
        core_secret_factories={},
        required_secret_names=(),
    )
    native.bind_request.return_value = request
    monkeypatch.setattr("lychd.system.services.tether.service.NativeTetherService", lambda: native)
    assemble = MagicMock()
    compile_direct = MagicMock(side_effect=AssertionError("Native helper units would be lost"))
    monkeypatch.setattr("lychd.cli.binding.assemble_bind_use_case", assemble)
    monkeypatch.setattr("lychd.cli.binding.compile_bind_request", compile_direct)
    session = BindingCommandSession(
        settings_snapshot=SettingsSnapshot.capture(settings),
        extensions=MagicMock(),
        runes=MagicMock(),
        soulstones=(),
        portals=(),
        preflight_service=MagicMock(),
        preflight=MagicMock(),
    )
    prepared = session.prepare()
    assert prepared.request is request
    assert dict(prepared.request.plain_units) == {"lychd-tether-runtime.service": "owned runtime helper"}
    assert assemble.call_args.kwargs["request_attestor"] == native.attest_bind_request
    assemble.return_value.plan.assert_called_once_with(request)
    compile_direct.assert_not_called()


def _attachment_document() -> dict[str, object]:
    import base64

    return {
        "id": "received",
        "remote_lich_id": "remote",
        "interface": "wgimport",
        "address": "10.77.0.2/24",
        "private_key_ref": "lychd-tether-client",
        "remote_public_key": base64.b64encode(b"\x01" * 32).decode(),
        "endpoint_address": "192.0.2.50",
        "endpoint_port": 51820,
        "services": [
            {
                "id": "api",
                "address": "10.77.0.1",
                "port": 8443,
                "hostname": "peer.test",
                "application_identity_ref": "remote-app",
            }
        ],
        "allowed_callers": ["intercom"],
    }


def test_register_dispatches_closed_attachment_without_other_lifecycle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json

    from lychd.domain.tether.models import ImportedAttachment

    path = tmp_path / "attachment.json"
    path.write_text(json.dumps(_attachment_document()))
    path.chmod(0o600)
    service = MagicMock()
    service.register_attachment.return_value = {"state": "registered", "changed": True, "attachment_id": "received"}
    monkeypatch.setattr("lychd.system.services.tether.service.NativeTetherService", lambda: service)
    result = CliRunner().invoke(tether_group, ["register", "--attachment-file", str(path), "--dry-run"])
    assert result.exit_code == 0, result.output
    expected = ImportedAttachment.model_validate_json(path.read_text(), strict=True)
    service.register_attachment.assert_called_once_with(expected, dry_run=True)
    assert [call[0] for call in service.method_calls] == ["register_attachment"]


@pytest.mark.parametrize("case", ["mode", "symlink", "parent_symlink", "hardlink", "oversize", "duplicate", "hook"])
def test_register_refuses_unsafe_or_unclosed_public_input(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import json
    import os

    path = tmp_path / "attachment.json"
    path.write_text(json.dumps(_attachment_document()))
    path.chmod(0o600)
    if case == "mode":
        path.chmod(0o644)
    elif case == "symlink":
        alias = tmp_path / "alias.json"
        alias.symlink_to(path)
        path = alias
    elif case == "parent_symlink":
        alias = tmp_path / "alias"
        alias.symlink_to(tmp_path, target_is_directory=True)
        path = alias / path.name
    elif case == "hardlink":
        os.link(path, tmp_path / "alias.json")
    elif case == "oversize":
        path.write_bytes(b" " * (64 * 1024 + 1))
    elif case == "duplicate":
        path.write_text('{"id":"received","id":"PRIVATE"}')
    else:
        path.write_text(json.dumps({**_attachment_document(), "PostUp": "PRIVATE"}))
    service = MagicMock()
    monkeypatch.setattr("lychd.system.services.tether.service.NativeTetherService", lambda: service)
    result = CliRunner().invoke(tether_group, ["register", "--attachment-file", str(path)])
    assert result.exit_code != 0
    assert "Public attachment declaration refused" in result.output
    assert "PRIVATE" not in result.output
    service.register_attachment.assert_not_called()


def test_register_native_failure_does_not_echo_declaration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import json

    path = tmp_path / "attachment.json"
    path.write_text(json.dumps(_attachment_document()))
    path.chmod(0o600)
    service = MagicMock()
    service.register_attachment.side_effect = ValueError("PRIVATE")
    monkeypatch.setattr("lychd.system.services.tether.service.NativeTetherService", lambda: service)
    result = CliRunner().invoke(tether_group, ["register", "--attachment-file", str(path)])
    assert result.exit_code != 0
    assert "PRIVATE" not in result.output
