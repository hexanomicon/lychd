"""Closed public intent and deterministic network projection contracts."""
# ruff: noqa: INP001 -- bounded test path; no package initializer is required.

from __future__ import annotations

import base64
import struct
from uuid import UUID

import pytest
from pydantic import ValidationError

from lychd.domain.tether.models import (
    CompiledTetherPlan,
    TetherEnvelope,
    TetherPeerIntent,
    compile_tether_plan,
    render_address_commands,
    render_authorized_key,
    render_nftables,
    render_sshd_config,
    render_wireguard_public,
)


def envelope(**overrides: object) -> TetherEnvelope:
    return TetherEnvelope.model_validate(
        {
            "installation_id": "11111111-1111-4111-8111-111111111111",
            "interface": "tether0",
            "server_address": "10.77.0.1/32",
            "udp_bind_address": "192.0.2.10",
            "udp_port": 51820,
            "advertised_endpoint": "192.0.2.10:51820",
            "image": "localhost/lychd-tether@sha256:" + "a" * 64,
            "wireguard_secret": {"purpose": "wireguard-server", "name": "tether-wg"},
            "ssh_host_secret": {"purpose": "ssh-host", "name": "tether-ssh"},
            "altar_port": 7134,
            **overrides,
        }
    )


def peer(**overrides: object) -> TetherPeerIntent:
    ssh_blob = struct.pack(">I", 11) + b"ssh-ed25519" + struct.pack(">I", 32) + b"s" * 32
    return TetherPeerIntent.model_validate(
        {
            "installation_id": "11111111-1111-4111-8111-111111111111",
            "generation": 1,
            "operation_id": "22222222-2222-4222-8222-222222222222",
            "peer_id": "operator",
            "wireguard_public_key": base64.b64encode(b"w" * 32).decode(),
            "address": "10.77.0.2/32",
            "ssh_authorized_public_key": "ssh-ed25519 " + base64.b64encode(ssh_blob).decode(),
            **overrides,
        }
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"command": "evil"},
        {"dns": "1.1.1.1"},
        {"routes": ["0.0.0.0/0"]},
        {"server_address": "10.77.0.1/24"},
        {"server_address": "127.0.0.1/32"},
        {"server_address": "169.254.1.1/32"},
        {"server_address": "192.0.2.1/32"},
        {"server_address": "::1/128"},
        {"interface": "lo"},
        {"interface": "wg0;true"},
        {"udp_port": 53},
        {"ssh_port": 22},
        {"udp_port": True},
        {"advertised_endpoint": "example.test:51820"},
        {"advertised_endpoint": "192.0.2.1:051820"},
        {"advertised_endpoint": "[::1]:51820"},
        {"image": "localhost/lychd-tether:latest"},
        {"wireguard_secret": {"purpose": "wireguard-server", "name": "tether-ssh"}},
        {"wireguard_secret": {"purpose": "ssh-host", "name": "tether-wg"}},
        {"wireguard_secret": {"purpose": "wireguard-server", "name": "key,target=/tmp/elsewhere"}},
        {"peer_limit": 2},
    ],
)
def test_envelope_refuses_unknown_or_widened_authority(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        envelope(**changes)


@pytest.mark.parametrize(
    "changes",
    [
        {"private_key": "never"},
        {"address": "0.0.0.0/0"},
        {"address": "10.77.0.2/24"},
        {"wireguard_public_key": "not-a-key"},
        {"wireguard_public_key": base64.b64encode(bytes(32)).decode()},
        {"ssh_authorized_public_key": "command=evil ssh-ed25519 key"},
        {"ssh_authorized_public_key": "ssh-ed25519 " + base64.b64encode(b"x" * 32).decode()},
        {"persistent_keepalive": 121},
        {"generation": 0},
        {"peer_id": "../../other"},
    ],
)
def test_peer_refuses_routes_private_keys_and_ssh_options(changes: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        peer(**changes)


def test_plan_is_deterministic_frozen_and_binds_exact_public_envelope() -> None:
    plan = compile_tether_plan(envelope())
    assert plan == compile_tether_plan(envelope())
    assert len(plan.envelope_digest) == 64
    assert plan.startup_order == (plan.guard_unit, plan.pod_unit, plan.wireguard_unit, plan.forwarder_unit)
    assert tuple(ref.purpose for ref in plan.secret_requirements) == ("wireguard-server", "ssh-host")
    assert plan.closure_relative_path == "tether/closed.json"
    assert "-u" not in plan.pasta_options
    assert "--dns-forward" in plan.pasta_options
    assert "169.254.1.1" in plan.pasta_options
    assert "--dns-host" in plan.pasta_options
    assert "--search" in plan.pasta_options
    assert "-T" in plan.pasta_options
    assert "127.0.0.1/7134" in plan.pasta_options
    with pytest.raises(ValidationError, match="frozen"):
        plan.envelope.altar_port = 8000
    with pytest.raises(ValidationError, match="digest"):
        CompiledTetherPlan.model_validate({**plan.model_dump(), "envelope_digest": "0" * 64})
    with pytest.raises(ValidationError):
        CompiledTetherPlan.model_validate({**plan.model_dump(), "pod_unit": "lychd-pod.service"})


@pytest.mark.parametrize(
    "changes",
    [
        {"address": "10.77.0.1/32"},
        {"state": "revoked"},
        {"installation_id": UUID(int=9)},
    ],
)
def test_projections_refuse_foreign_revoked_or_overlapping_peer(changes: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="Tether peer"):
        render_wireguard_public(compile_tether_plan(envelope()), peer(**changes))


def test_policy_has_three_default_deny_chains_and_exact_public_flows() -> None:
    plan, intent = compile_tether_plan(envelope()), peer()
    nft = render_nftables(plan, intent)
    assert nft.count("policy drop;") == 3
    assert 'iifname "tether0" ip saddr 10.77.0.2 ip daddr 10.77.0.1 tcp dport 2222' in nft
    assert 'oifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp dport 7134' in nft
    assert 'iifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp dport 7134 ct state new,established accept' in nft
    assert 'oifname "lo" ip saddr 127.0.0.1 ip daddr 127.0.0.1 tcp sport 7134 ct state established accept' in nft
    assert "meta nfproto ipv4 udp sport 51820" in nft
    assert "ip6" not in nft
    assert "dport 53" not in nft
    assert "ct state established accept\n" in nft
    assert "0.0.0.0/0" not in nft
    commands = render_address_commands(plan, intent)
    assert ("route", "add", "10.77.0.2/32", "dev", "tether0") in commands
    projection = render_wireguard_public(plan, intent)
    assert projection.ssh_port == 2222
    assert projection.altar_port == 7134
    assert "private" not in projection.model_dump_json().lower()


def test_sshd_and_authorized_key_close_every_other_channel() -> None:
    plan, intent = compile_tether_plan(envelope()), peer()
    config = render_sshd_config(plan)
    for line in (
        "ListenAddress 10.77.0.1",
        "Port 2222",
        "PermitOpen 127.0.0.1:7134",
        "MaxSessions 0",
        "AllowTcpForwarding local",
        "AllowStreamLocalForwarding no",
        "PermitListen none",
        "AllowAgentForwarding no",
        "X11Forwarding no",
        "PermitTTY no",
        "UseDNS no",
    ):
        assert line in config.splitlines()
    assert render_authorized_key(plan, intent).startswith(
        'restrict,port-forwarding,permitopen="127.0.0.1:7134" ssh-ed25519 '
    )


def test_dns_denial_precedes_both_wireguard_transport_exceptions() -> None:
    policy = render_nftables(compile_tether_plan(envelope()), peer())
    assert policy.count("udp dport { 53, 853 } drop") == 2
    assert policy.count("tcp dport { 53, 853 } drop") == 2
    for chain, exception in (
        ("input", "meta nfproto ipv4 udp dport 51820 accept"),
        ("output", "meta nfproto ipv4 udp sport 51820 accept"),
    ):
        start = policy.index(f" chain {chain} {{")
        end = policy.index("\n }", start)
        body = policy[start:end]
        assert body.index("udp dport { 53, 853 } drop") < body.index(exception)
        assert body.index("tcp dport { 53, 853 } drop") < body.index(exception)
