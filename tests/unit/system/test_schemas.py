from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from lychd.system.schemas import MountData, QuadletContainer, QuadletPod, QuadletTarget, podman_secret_source


def test_mountdata_from_str_marks_non_symmetric_mount_as_not_mirrored() -> None:
    mount = MountData.from_str("/host/models:/models:ro,Z")

    assert mount.host_path == Path("/host/models")
    assert mount.container_path == Path("/models")
    assert mount.mirror is False


def test_mountdata_rejects_mirror_true_for_non_symmetric_paths() -> None:
    with pytest.raises(ValueError, match="mirror=True requires identical host_path and container_path"):
        MountData.model_validate(
            {
                "host_path": "/host/models",
                "container_path": "/models",
                "mirror": True,
                "options": ["ro", "Z"],
            }
        )


@pytest.mark.parametrize("option", ["x\nExec=/bin/sh", "idmap=uids=0-1-1", ""])
def test_mountdata_rejects_unbounded_or_injected_options(option: str) -> None:
    with pytest.raises(ValueError, match="unsafe volume option|Unsupported"):
        MountData.from_str(f"/data/models:/models:ro,{option}")


@pytest.mark.parametrize(
    "override",
    [
        {"env_vars": {"SAFE": "ok\nExec=/bin/sh"}},
        {"devices": ["nvidia.com/gpu=all\nExec=/bin/sh"]},
        {"env_vars": {"SAFE": "%h"}},
        {"description": "swallow-next-directive\\"},
        {"env_vars": {"SAFE": r"\x25h"}},
        {"image": "${HOST_IMAGE}"},
        {"exec": "serve ${HOST_COMMAND}"},
        {"devices": ["${HOST_DEVICE}"]},
        {"podman_args": ["--root=${HOST_ROOT}"]},
        {"secrets": ["safe,target=/${HOST_ROOT}/secret"]},
        {"exec": shlex.join([";", "/bin/touch", "/tmp/pwned"])},  # noqa: S108
        {"podman_args": ["';'"]},
    ],
)
def test_quadlet_container_rejects_directive_and_specifier_injection(
    override: dict[str, object],
) -> None:
    payload = {
        "description": "safe",
        "image": "registry.example/runtime:1",
        "container_name": "safe",
        **override,
    }
    with pytest.raises(
        ValueError,
        match="single-line|specifier|backslash|environment expansion|command separator",
    ):
        QuadletContainer.model_validate(payload)


@pytest.mark.parametrize(
    "spec",
    [
        '"core",target=/run/stolen',
        r"core\x2ctarget=/run/stolen",
        "core,target=relative",
        "core,target=/run/../stolen",
        'core,target=/app/".."/stolen',
        "core,target=/app/'..'/stolen",
        "core,target=/run/stolen,mode=not-octal",
        "core,target=/run/stolen,target=/run/again",
        "core,uid=1000",
    ],
)
def test_podman_secret_specs_use_a_bounded_unambiguous_grammar(spec: str) -> None:
    with pytest.raises(ValueError, match="Podman secret"):
        podman_secret_source(spec)


def test_podman_secret_spec_returns_the_validated_source() -> None:
    assert podman_secret_source("tabby_auth,target=/app/api_tokens.yml,mode=0444") == "tabby_auth"


@pytest.mark.parametrize(
    ("host_path", "container_path"),
    [
        ('/home/magus/.config/"lychd"', "/models"),
        ("/models", "/home/magus/.config/'lychd'"),
    ],
)
def test_mountdata_rejects_systemd_quote_canonicalization(
    host_path: str,
    container_path: str,
) -> None:
    with pytest.raises(ValueError, match="volume delimiters|quote characters"):
        MountData(host_path=Path(host_path), container_path=Path(container_path), mirror=False)


@pytest.mark.parametrize(
    ("host_path", "container_path"),
    [("/models:ro", "/models"), ("/models", "/models:ro")],
)
def test_mountdata_rejects_ambiguous_volume_delimiters(
    host_path: str,
    container_path: str,
) -> None:
    with pytest.raises(ValueError, match="volume delimiters"):
        MountData(host_path=Path(host_path), container_path=Path(container_path), mirror=False)


@pytest.mark.parametrize(
    ("host_path", "container_path"),
    [("/${HOME}/.config/lychd", "/models"), ("/models", "/${HOME}/.config/lychd")],
)
def test_mountdata_rejects_systemd_environment_expansion(
    host_path: str,
    container_path: str,
) -> None:
    with pytest.raises(ValueError, match="systemd environment expansion"):
        MountData(host_path=Path(host_path), container_path=Path(container_path), mirror=False)


@pytest.mark.parametrize(
    "mapping",
    [
        "127.0.0.1:9999:9999\nNetwork=host",
        "127.0.0.1:0:9999",
        "127.0.0.1:65536:9999",
        "127.0.0.1:9999:9999:udp",
        "0.0.0.0:9999:9999",
    ],
)
def test_quadlet_pod_rejects_unsafe_publish_port_mappings(mapping: str) -> None:
    with pytest.raises(ValueError, match="PublishPort|single-line"):
        QuadletPod(publish_ports=[mapping])


def test_quadlet_pod_rejects_duplicate_host_ports() -> None:
    with pytest.raises(ValueError, match="duplicate host port 9999"):
        QuadletPod(publish_ports=["127.0.0.1:9999:8000", "127.0.0.1:9999:8001"])


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "logic\nWantedBy=default.target", "description": "safe"},
        {"name": "logic", "description": "swallow\\"},
        {"name": "logic", "description": "safe", "part_of": r"safe\x25h.service"},
    ],
)
def test_quadlet_target_rejects_directive_and_escape_injection(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="single-line|backslash"):
        QuadletTarget.model_validate(payload)
