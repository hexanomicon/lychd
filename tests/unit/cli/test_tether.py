"""Bootstrap-safe closed native grammar, with no private-key option or callback."""

from __future__ import annotations

from click.testing import CliRunner

from lychd.__main__ import cli


def test_closed_native_tether_grammar_and_no_extra_roots() -> None:
    runner = CliRunner()
    root = runner.invoke(cli, ["--help"])
    assert root.exit_code == 0
    assert "run" in root.output
    group = runner.invoke(cli, ["run", "tether", "--help"])
    assert group.exit_code == 0
    for command in ("prepare", "enroll", "inspect", "revoke"):
        assert command in group.output
    assert runner.invoke(cli, ["run", "arbitrary"]).exit_code == 2
    assert runner.invoke(cli, ["tether-close"]).exit_code == 2
    assert runner.invoke(cli, ["run", "tether", "execute"]).exit_code == 2


def test_enrollment_accepts_only_public_client_keys_and_no_path_unit_or_argv() -> None:
    help_result = CliRunner().invoke(cli, ["run", "tether", "enroll", "--help"])
    assert help_result.exit_code == 0
    assert "--wireguard-public-key" in help_result.output
    assert "--ssh-public-key" in help_result.output
    assert "--private-key" not in help_result.output
    for forbidden in ("--command", "--unit", "--path", "--image"):
        assert forbidden not in help_result.output
