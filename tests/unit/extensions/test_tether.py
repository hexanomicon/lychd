"""Tether selection retains provenance and compiles only its closed service body."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from lychd.config.runes.registry import RuneRegistry
from lychd.config.settings.root import Settings
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import (
    QuadletContribution,
    RegisteredQuadletContributor,
    TransmutationContext,
    Transmuter,
)
from lychd.domain.tether.models import TetherEnvelope
from lychd.extensions.builtin.tether.config import TetherSettings
from lychd.extensions.builtin.tether.contributor import TetherQuadletContributor
from lychd.extensions.host import assemble_extensions
from lychd.system.schemas import QuadletContainer, QuadletPod, QuadletTetherPod
from lychd.system.services.bind import BindRequest
from lychd.system.services.bind_compilation import compile_bind_request
from lychd.system.services.scribe import ScribeService


def _rune(**overrides: object) -> TetherSettings:
    return TetherSettings.model_validate(
        {
            "installation_id": "11111111-1111-4111-8111-111111111111",
            "interface": "tether0",
            "server_address": "10.77.0.1/32",
            "udp_bind_address": "192.0.2.10",
            "udp_port": 51820,
            "advertised_endpoint": "192.0.2.10:51820",
            "quadlet": {"image": "localhost/lychd-tether@sha256:" + "a" * 64},
            "wireguard_secret": {"purpose": "wireguard-server", "name": "tether-wg"},
            "ssh_host_secret": {"purpose": "ssh-host", "name": "tether-ssh"},
            **overrides,
        }
    )


def _settings() -> Settings:
    return Settings.model_validate({"extensions": {"builtins": ["tether"]}})


def _compiler(settings: Settings | None = None) -> Transmuter:
    settings = settings or _settings()
    return Transmuter(
        settings=settings,
        runtime_planner=RuntimeAdapterRegistry(),
        contributors=assemble_extensions(settings).quadlet_registrations,
    )


def test_manager_assigned_tether_identity_survives_assembly() -> None:
    extensions = assemble_extensions(_settings())
    assert TetherSettings in extensions.rune_schemas
    assert [(item.registrant_id, type(item.contributor)) for item in extensions.quadlet_registrations] == [
        ("builtin:tether", TetherQuadletContributor),
    ]


def test_tether_cannot_change_core_or_join_its_pod() -> None:
    compiler = _compiler()
    baseline = compiler.transmute_all((), runes=RuneRegistry(()))
    complete = compiler.transmute_all((), runes=RuneRegistry((_rune(),)))
    assert complete[: len(baseline)] == baseline
    assert len(complete) == len(baseline) + 3
    pod = next(item for item in complete if isinstance(item, QuadletTetherPod))
    assert pod.udp_port == 51820
    assert pod.altar_port == _settings().server.port
    core_pod = next(item for item in complete if isinstance(item, QuadletPod))
    assert all("udp" not in port for port in core_pod.publish_ports)
    roles = [item for item in complete if isinstance(item, QuadletContainer) and item.tether_role]
    assert [item.tether_role for item in roles] == ["wireguard", "forwarder"]
    assert all(item.pod == "lychd-tether.pod" and item.user == "0" for item in roles)
    assert roles[1].binds_to == ["lychd-tether-guard.path", "lychd-tether-wg.service"]
    assert roles[1].requires == ["lychd-tether-wg.service"]
    assert all(item.restart_policy == "no" and not item.wanted_by for item in roles)
    assert [item.secrets[0].split(",")[0] for item in roles] == ["tether-wg", "tether-ssh"]


@dataclass(frozen=True)
class _EnvelopeContributor:
    tether: TetherEnvelope
    registrant_id: str = "builtin:tether"

    def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
        del ctx
        return QuadletContribution(tether=self.tether)


@pytest.mark.parametrize("registrant", [None, "crypt:tether", "builtin:observability/phoenix", "builtin:tether-forged"])
def test_self_asserted_tether_identity_cannot_grant_udp_or_network_capability(registrant: str | None) -> None:
    contributor = _EnvelopeContributor(_rune().envelope(altar_port=7134))
    registered = RegisteredQuadletContributor(registrant, contributor) if registrant else contributor
    compiler = Transmuter(settings=_settings(), runtime_planner=RuntimeAdapterRegistry(), contributors=(registered,))
    with pytest.raises(ValueError, match="manager-assigned"):
        compiler.transmute_all(())


def test_raw_role_replay_is_refused_even_under_the_tether_registrant() -> None:
    compiler = _compiler()
    manifests = compiler.transmute_all((), runes=RuneRegistry((_rune(),)))
    role = next(item for item in manifests if isinstance(item, QuadletContainer) and item.tether_role)

    class Replay:
        def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
            del ctx
            return QuadletContribution(containers=(role,))

    replay = Transmuter(
        settings=_settings(),
        runtime_planner=RuntimeAdapterRegistry(),
        contributors=(RegisteredQuadletContributor("builtin:tether", Replay()),),
    )
    with pytest.raises(ValueError, match="compiler-owned"):
        replay.transmute_all(())


def test_tether_secret_cannot_alias_a_core_secret() -> None:
    rune = _rune(wireguard_secret={"purpose": "wireguard-server", "name": _settings().server.web.secret_key_secret})
    with pytest.raises(ValueError, match="disjoint"):
        _compiler().transmute_all((), runes=RuneRegistry((rune,)))


def test_bind_requires_exact_guard_fileset_and_detects_both_secrets() -> None:
    settings = _settings()

    def compile_request(units: Mapping[str, str] | None = None) -> BindRequest:
        return compile_bind_request(
            settings=settings,
            extensions=assemble_extensions(settings),
            runes=RuneRegistry((_rune(),)),
            soulstones=(),
            portals=(),
            tether_plain_units=units,
        )

    request = compile_request()
    trusted = {name: content for name, content in request.plain_units if name.startswith("lychd-tether-")}
    assert compile_request(trusted).plain_units == request.plain_units
    for altered in (
        {},
        {"lychd-other.service": "[Service]\n"},
        {"lychd-tether-guard.path": trusted["lychd-tether-guard.path"]},
        {**trusted, "lychd-tether-close.service": "[Service]\nType=oneshot\n"},
    ):
        with pytest.raises(ValueError, match="guard and closure"):
            compile_request(altered)
    assert request.required_secret_names == ("tether-ssh", "tether-wg")
    assert {
        "lychd-reactor.path",
        "lychd-reactor.service",
        "lychd-tether-guard.path",
        "lychd-tether-close.service",
    } == set(request.plain_unit_mapping())


def test_scribe_renders_tether_with_one_complete_manifest(tmp_path: Path) -> None:
    compiler = _compiler()
    manifests = compiler.transmute_all((), runes=RuneRegistry((_rune(),)))
    output, systemd = tmp_path / "quadlet", tmp_path / "systemd"
    output.mkdir()
    systemd.mkdir()
    scribe = ScribeService(output_dir=output, systemd_dir=systemd)
    scribe.reconcile_all(manifests, plain_units={})
    pod = (output / "lychd-tether.pod").read_text()
    wg = (output / "lychd-tether-wg.container").read_text()
    ssh = (output / "lychd-tether-ssh.container").read_text()
    assert "PublishPort=192.0.2.10:51820:51820/udp" in pod
    assert "-T,127.0.0.1/7134,-U,none" in pod
    assert "--map-host-loopback,none,--map-guest-addr,none" in pod
    assert "--dns,none,--dns-forward,169.254.1.1,--dns-host,127.0.0.1,--search,none,--no-dhcp-dns" in pod
    assert ",-u,none" not in pod
    assert "DNS=none" in pod
    assert "PodmanArgs=--no-hosts" in pod
    assert "BindsTo=lychd-tether-guard.path" in pod
    assert "UserNS=keep-id" not in pod
    assert "DropCapability=all" in wg
    assert "AddCapability=CAP_NET_ADMIN" in wg
    assert "Notify=true" in wg
    assert "AddCapability=CAP_SETUID CAP_SETGID CAP_SYS_CHROOT" in ssh
    assert "CAP_NET_ADMIN" not in ssh
    assert "ReadOnlyTmpfs=false" in wg
    assert "size=8m" in wg
    assert "KillMode=control-group" in wg
    assert "Secret=tether-wg,type=mount,target=/run/secrets/tether-wg-server,mode=0400" in wg
    assert "Secret=tether-ssh,type=mount,target=/run/secrets/tether-ssh-host,mode=0400" in ssh
    assert "Pod=lychd.pod" not in wg
    assert "Pod=lychd.pod" not in ssh
    assert "WantedBy=default.target" not in pod + wg + ssh
    assert (output / "lychd.pod").is_file()


@pytest.mark.parametrize("identity", ["lychd-tether", "lychd-tether-wg", "lychd-tether-ssh"])
def test_ordinary_container_cannot_shadow_a_tether_identity(identity: str) -> None:
    class Shadow:
        def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
            del ctx
            return QuadletContribution(
                containers=(
                    QuadletContainer(
                        description="ordinary",
                        image="example/ordinary",
                        container_name=identity,
                    ),
                )
            )

    compiler = Transmuter(settings=_settings(), runtime_planner=RuntimeAdapterRegistry(), contributors=(Shadow(),))
    with pytest.raises(ValueError, match="reserved Tether"):
        compiler.transmute_all(())


def test_ordinary_container_cannot_conflict_with_the_closure_handler() -> None:
    class Sabotage:
        def contribute(self, ctx: TransmutationContext) -> QuadletContribution:
            del ctx
            return QuadletContribution(
                containers=(
                    QuadletContainer(
                        description="ordinary",
                        image="example/ordinary",
                        container_name="lychd-extra",
                        conflicts=["lychd-tether-close.service"],
                    ),
                )
            )

    compiler = Transmuter(settings=_settings(), runtime_planner=RuntimeAdapterRegistry(), contributors=(Sabotage(),))
    with pytest.raises(ValueError, match="reserved Tether"):
        compiler.transmute_all(())


def test_tether_host_hooks_are_fixed_and_quote_the_installed_python(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from lychd.system import constants
    from lychd.system.schemas import systemd_environment_assignment
    from lychd.system.services.scribe import rendering

    compiler = _compiler()
    manifests = compiler.transmute_all((), runes=RuneRegistry((_rune(),)))
    config_home = tmp_path / 'codex path "quoted" $literal'
    data_home, cache_home = tmp_path / "data path", tmp_path / "cache path"
    monkeypatch.setattr(constants, "PATH_XDG_CONFIG_HOME", config_home)
    monkeypatch.setattr(constants, "PATH_XDG_DATA_HOME", data_home)
    monkeypatch.setattr(constants, "PATH_XDG_CACHE_HOME", cache_home)
    installed_prefix = tmp_path / "trusted installation"
    monkeypatch.setattr(rendering.sys, "prefix", str(installed_prefix))
    output, systemd = tmp_path / "quadlet", tmp_path / "systemd"
    output.mkdir()
    systemd.mkdir()
    scribe = ScribeService(output_dir=output, systemd_dir=systemd)
    scribe.reconcile_all(manifests, plain_units={})
    python = f'"{installed_prefix}/bin/python"'
    for filename, role in (
        ("lychd-tether.pod", "pod"),
        ("lychd-tether-wg.container", "wireguard"),
        ("lychd-tether-ssh.container", "forwarder"),
    ):
        lines = (output / filename).read_text().splitlines()
        assert f"ExecStartPre={python} -m lychd.system.services.tether.composition preflight-{role}" in lines
        assert f"ExecStartPost={python} -m lychd.system.services.tether.composition attest-{role}" in lines
        expected_preflight = [f"ExecStartPre={python} -m lychd.system.services.tether.composition preflight-{role}"]
        if role == "pod":
            expected_preflight.append(f"ExecStartPre={python} -m lychd.system.services.tether.composition begin-pod")
        assert [line for line in lines if line.startswith("ExecStartPre=")] == expected_preflight
        for key, value in {
            "HOME": str(Path.home()),
            "XDG_CONFIG_HOME": str(config_home),
            "XDG_DATA_HOME": str(data_home),
            "XDG_CACHE_HOME": str(cache_home),
        }.items():
            assert f"Environment={systemd_environment_assignment(key, value)}" in lines
        assert sum(line.startswith("ExecStartPost=") for line in lines) == 1
    forwarder = (output / "lychd-tether-ssh.container").read_text().splitlines()
    assert "After=lychd-tether-guard.path lychd-tether-pod.service lychd-tether-wg.service" in forwarder
    assert "BindsTo=lychd-tether-guard.path lychd-tether-wg.service" in forwarder
    for filename in ("lychd.pod", "lychd-vessel.container", "lychd-phylactery.container", "lychd-migrate.container"):
        assert "lychd.system.services.tether.composition" not in (output / filename).read_text()


@pytest.mark.parametrize("unsafe", ["host%U", "host$TOKEN", "host\\continuation", 'host"quoted', "host;command"])
def test_tether_renderer_refuses_unsafe_installed_python_tokens(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    unsafe: str,
) -> None:
    from lychd.system.services.scribe import rendering

    compiler = _compiler()
    manifests = compiler.transmute_all((), runes=RuneRegistry((_rune(),)))
    monkeypatch.setattr(rendering.sys, "prefix", str(tmp_path / unsafe))
    output, systemd = tmp_path / "quadlet", tmp_path / "systemd"
    output.mkdir()
    systemd.mkdir()
    scribe = ScribeService(output_dir=output, systemd_dir=systemd)
    with pytest.raises(ValueError, match="systemd"):
        scribe.reconcile_all(manifests, plain_units={})
    assert not tuple(output.iterdir())
    assert not tuple(systemd.iterdir())
