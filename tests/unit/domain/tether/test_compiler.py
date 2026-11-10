from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from lychd.config.quadlet import QuadletConfig
from lychd.domain.animation.transmute import QuadletContribution, Transmuter
from lychd.domain.tether.compiler import TetherDeployment, compile_tether
from lychd.domain.tether.models import (
    AttachmentAdmission,
    ImportedAttachment,
    ImportedService,
    OfferedNetwork,
    OfferedPeer,
    OfferedService,
    OwnerAccess,
    TetherRune,
    TetherSnapshot,
)
from lychd.system.schemas import QuadletContainer, QuadletPod, TetherPodPolicy

EPOCH = "ab" * 16
KEY = base64.b64encode(bytes(range(32))).decode()
KEY2 = base64.b64encode(bytes(range(1, 33))).decode()
SSH_KEY = "ssh-ed25519 " + base64.b64encode(b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20" + bytes(range(32))).decode()


def attachment(name: str) -> ImportedAttachment:
    return ImportedAttachment(
        id=name,
        remote_lich_id=name,
        interface="wg0",
        address="10.77.0.1/32",
        private_key_ref=f"lychd-tether-{name}-private",
        remote_public_key=KEY,
        endpoint_address="198.51.100.10",
        endpoint_port=51820,
        services=(
            ImportedService(
                id="intercom", address="10.77.0.2", port=443, hostname=f"{name}.example", application_identity_ref=name
            ),
        ),
        allowed_callers=("intercom",),
    )


def project(rune: TetherRune, snapshot: TetherSnapshot) -> TetherDeployment:
    return compile_tether(
        rune=rune,
        snapshot=snapshot,
        runtime_root=Path("/run/user/1000/lychd-tether"),
        config_root=Path("/var/lib/example/tether-config"),
        core_web_port=8123,
        consumer_uid=1000,
    )


def test_overlapping_imported_addresses_have_distinct_selection_and_socket() -> None:
    rune = TetherRune(quadlet=QuadletConfig(image="example/tether:1"), attachments=(attachment("b"), attachment("c")))
    snapshot = TetherSnapshot(
        installation_epoch=EPOCH,
        attachments=(
            AttachmentAdmission(attachment_id="b", generation=3),
            AttachmentAdmission(attachment_id="c", generation=2),
        ),
    )
    result = project(rune, snapshot)
    assert len(result.routes) == 2
    assert {row.address for row in result.routes} == {"10.77.0.2"}
    assert len({row.socket_path for row in result.routes}) == 2
    assert len({network.pod_unit for network in result.networks}) == 2
    assert result.consumer_mount is not None
    assert result.consumer_mount.options == ["ro", "z"]
    assert all(manifest.pod != "lychd.pod" for manifest in result.manifests if isinstance(manifest, QuadletContainer))
    assert project(rune, snapshot) == result


def test_revoking_one_attachment_preserves_the_other_exact_projection() -> None:
    rune = TetherRune(quadlet=QuadletConfig(image="example/tether:1"), attachments=(attachment("b"), attachment("c")))
    before = TetherSnapshot(
        installation_epoch=EPOCH,
        attachments=(
            AttachmentAdmission(attachment_id="b", generation=1),
            AttachmentAdmission(attachment_id="c", generation=2),
        ),
    )
    after = before.model_copy(
        update={
            "attachments": (AttachmentAdmission(attachment_id="b", generation=2, enabled=False), before.attachments[1])
        }
    )
    old = project(rune, before)
    new = project(rune, after)
    assert new.routes == (old.routes[1],)
    assert new.networks == (old.networks[1],)
    assert new.runtime_configs == tuple(config for config in old.runtime_configs if config.network_id == "c")
    assert "lychd-tether-b-private" not in new.required_secrets


def test_generation_and_installation_epoch_change_socket_identity() -> None:
    rune = TetherRune(quadlet=QuadletConfig(image="example/tether:1"), attachments=(attachment("b"),))
    snapshot = TetherSnapshot(
        installation_epoch=EPOCH, attachments=(AttachmentAdmission(attachment_id="b", generation=1),)
    )
    old = project(rune, snapshot).routes[0]
    changed_generation = snapshot.model_copy(
        update={"attachments": (AttachmentAdmission(attachment_id="b", generation=2),)}
    )
    changed_epoch = snapshot.model_copy(update={"installation_epoch": "cd" * 16})
    assert old.socket_path != project(rune, changed_generation).routes[0].socket_path
    assert old.socket_path != project(rune, changed_epoch).routes[0].socket_path


def test_one_offered_interface_many_independent_owner_adapters() -> None:
    offered = OfferedNetwork(
        id="home",
        interface="wg0",
        address="10.55.0.1/24",
        listen_address="192.0.2.10",
        listen_port=51820,
        private_key_ref="lychd-tether-home-private",
    )
    rune = TetherRune(quadlet=QuadletConfig(image="example/tether:1"), offered=offered)
    peers = tuple(
        OfferedPeer(
            id=name,
            generation=1,
            public_key=key,
            address=address,
            owner_access=OwnerAccess(
                ssh_public_key=SSH_KEY, ssh_host_key_ref=f"lychd-tether-ssh-{name}", listen_port=port
            ),
        )
        for name, key, address, port in (("a", KEY, "10.55.0.2", 2222), ("b", KEY2, "10.55.0.3", 2223))
    )
    result = project(rune, TetherSnapshot(installation_epoch=EPOCH, offered_peers=peers))
    configs = result.runtime_configs
    assert [config.role for config in configs].count("wireguard") == 1
    assert [config.role for config in configs].count("owner-ssh") == 2
    assert len({config.name for config in configs}) == 3
    for config in configs:
        assert "private_key" not in json.dumps(config.payload).replace("private_key_path", "")
        if config.role == "owner-ssh":
            assert config.payload["target_port"] == 8123
            assert config.payload["target_address"] == "127.0.0.1"
    pod = next(manifest for manifest in result.manifests if isinstance(manifest, QuadletPod))
    assert pod.tether_policy is not None
    assert pod.tether_policy.owner_loopback_port == 8123
    assert pod.publish_ports == []
    revoked = peers[0].model_copy(update={"generation": 2, "enabled": False})
    changed = project(rune, TetherSnapshot(installation_epoch=EPOCH, offered_peers=(revoked, peers[1])))
    old_owner = next(config for config in configs if config.role == "owner-ssh" and config.payload["peer_id"] == "b")
    new_owner = next(config for config in changed.runtime_configs if config.role == "owner-ssh")
    assert old_owner.payload == new_owner.payload
    old_unit = next(
        manifest
        for manifest in result.manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == old_owner.name
    )
    new_unit = next(
        manifest
        for manifest in changed.manifests
        if isinstance(manifest, QuadletContainer) and manifest.container_name == new_owner.name
    )
    assert old_unit == new_unit


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("endpoint_address", "example.com"),
        ("endpoint_address", "127.0.0.1"),
        ("address", "10.77.0.1/0"),
        ("PostUp", "touch /tmp/owned"),
        ("dns_policy", "host"),
        ("endpoint_port", True),
    ],
)
def test_imported_intent_rejects_ambient_or_executable_input(field: str, value: object) -> None:
    payload = attachment("b").model_dump()
    payload[field] = value
    with pytest.raises(ValidationError):
        ImportedAttachment.model_validate(payload)


def test_snapshot_cannot_duplicate_peer_address_or_key() -> None:
    peer = OfferedPeer(id="a", generation=1, public_key=KEY, address="10.55.0.2")
    with pytest.raises(ValidationError, match="unique"):
        TetherSnapshot(installation_epoch=EPOCH, offered_peers=(peer, peer.model_copy(update={"id": "b"})))


def test_generic_contributor_cannot_claim_tether_capabilities() -> None:
    body = QuadletContainer(
        description="Tether",
        image="example/tether:1",
        container_name="lychd-tether-test",
        pod="lychd-tether-test.pod",
        user="0",
        read_only=True,
        tether_role="wireguard",
        run_init=False,
        wanted_by=[],
    )
    with pytest.raises(ValueError, match="host admission"):
        Transmuter._normalize_contribution(QuadletContribution(containers=(body,)))


def test_tether_profile_refuses_core_pod_and_generic_port_widening() -> None:
    with pytest.raises(ValidationError, match="own explicitly"):
        QuadletPod(tether_policy=TetherPodPolicy(kind="imported"), wanted_by=[])
    with pytest.raises(ValidationError, match=r"127\.0\.0\.1"):
        QuadletPod(publish_ports=["0.0.0.0:51820:51820/udp"])
    with pytest.raises(ValidationError, match="standalone"):
        QuadletContainer(
            description="bad",
            image="example/tether:1",
            container_name="lychd-tether-test",
            pod="lychd.pod",
            user="0",
            read_only=True,
            tether_role="wireguard",
            run_init=False,
            wanted_by=[],
        )


def test_secret_reference_cannot_cross_credential_purposes() -> None:
    imported = attachment("b")
    imported = imported.model_copy(update={"preshared_key_ref": imported.private_key_ref})
    rune = TetherRune(quadlet=QuadletConfig(image="example/tether:1"), attachments=(imported,))
    snapshot = TetherSnapshot(
        installation_epoch=EPOCH, attachments=(AttachmentAdmission(attachment_id="b", generation=1),)
    )
    with pytest.raises(ValueError, match="credential-purpose"):
        project(rune, snapshot)


def test_network_policy_cannot_smuggle_raw_pasta_arguments() -> None:
    with pytest.raises(ValidationError, match="closed pasta"):
        TetherPodPolicy(kind="imported", network="host")


def test_current_snapshot_must_reference_declared_attachment() -> None:
    rune = TetherRune(quadlet=QuadletConfig(image="example/tether:1"))
    snapshot = TetherSnapshot(
        installation_epoch=EPOCH, attachments=(AttachmentAdmission(attachment_id="unknown", generation=1),)
    )
    with pytest.raises(ValueError, match="undeclared"):
        project(rune, snapshot)


@pytest.mark.parametrize(
    ("address", "port"),
    [
        ("192.0.2.10", 443),
        ("169.254.1.2", 443),
        ("10.55.0.2", 443),
        ("192.0.2.20", 8000),
        ("192.0.2.20", 5432),
        ("192.0.2.20", 8123),
    ],
)
def test_external_backend_refuses_host_or_core_destinations(address: str, port: int) -> None:
    rune = TetherRune(
        quadlet=QuadletConfig(image="example/tether:1"),
        offered=OfferedNetwork(
            id="home",
            interface="wg0",
            address="10.55.0.1/24",
            listen_address="192.0.2.10",
            listen_port=51820,
            private_key_ref="lychd-tether-home-private",
            services=(OfferedService(id="external", listen_port=9443, backend_address=address, backend_port=port),),
        ),
    )
    snapshot = TetherSnapshot(installation_epoch=EPOCH)
    with pytest.raises(ValueError, match="admission context"):
        project(rune, snapshot)
    with pytest.raises(ValueError, match=r"backend|SSH profile"):
        compile_tether(
            rune=rune,
            snapshot=snapshot,
            runtime_root=Path("/run/user/1000/lychd-tether"),
            config_root=Path("/var/lib/example/tether-config"),
            core_web_port=8123,
            consumer_uid=1000,
            forbidden_backend_addresses=("192.0.2.10",),
        )


@pytest.mark.parametrize("interface", ["lo", "eth0", "tap0"])
def test_imported_interface_cannot_replace_namespace_device(interface: str) -> None:
    payload = attachment("b").model_dump()
    payload["interface"] = interface
    with pytest.raises(ValidationError, match="reserved"):
        ImportedAttachment.model_validate(payload)


def test_outer_endpoint_cannot_enter_tunnel_connected_route() -> None:
    payload = attachment("b").model_dump()
    payload.update(address="10.77.0.1/24", endpoint_address="10.77.0.254")
    with pytest.raises(ValidationError, match="local tunnel prefix"):
        ImportedAttachment.model_validate(payload)
