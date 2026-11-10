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
