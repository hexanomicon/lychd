from __future__ import annotations

import shlex
from pathlib import Path

import pytest

from lychd.system.schemas import MountData, QuadletContainer, QuadletPod, QuadletTarget, podman_secret_source
from lychd.system.unit_names import (
    animator_service_stem,
    animator_service_unit,
    animator_target_unit,
    coven_target_unit,
)


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
    with pytest.raises(ValueError, match=r"unsafe volume option|Unsupported"):
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
        match=r"single-line|specifier|backslash|environment expansion|command separator",
    ):
        QuadletContainer.model_validate(payload)


@pytest.mark.parametrize("name", ["../runtime", "runtime/sidecar", r"runtime\sidecar", "runtime..service"])
def test_quadlet_container_rejects_unsafe_name_components(name: str) -> None:
    with pytest.raises(ValueError, match="safe unit-name component"):
        QuadletContainer(
            description="safe",
            image="registry.example/runtime:1",
            container_name=name,
        )


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (QuadletContainer, {"pod": ".."}),
        (QuadletContainer, {"wants": ["safe.service", ".."]}),
        (QuadletPod, {"pod_name": ".."}),
        (QuadletPod, {"wanted_by": ["default.target", ".."]}),
        (QuadletTarget, {"name": "logic", "description": "safe", "requires": [".."]}),
    ],
)
def test_generated_manifests_reject_traversal_as_a_unit_reference(
    model: type[QuadletContainer | QuadletPod | QuadletTarget],
    payload: dict[str, object],
) -> None:
    if model is QuadletContainer:
        payload = {
            "description": "safe",
            "image": "registry.example/runtime:1",
            "container_name": "safe",
            **payload,
        }

    with pytest.raises(ValueError, match="safe unit-name component"):
        model.model_validate(payload)


@pytest.mark.parametrize(
    ("model", "payload"),
    [
        (
            QuadletContainer,
            {
                "description": "safe",
                "image": "registry.example/runtime:1",
                "container_name": "safe",
                "wants": ["same.service", "same.service"],
            },
        ),
        (QuadletPod, {"wanted_by": ["default.target", "default.target"]}),
        (
            QuadletTarget,
            {
                "name": "logic",
                "description": "safe",
                "wants": ["lychd-animator-alpha.target", "lychd-animator-alpha.target"],
            },
        ),
    ],
)
def test_generated_manifests_reject_duplicate_unit_references(
    model: type[QuadletContainer | QuadletPod | QuadletTarget],
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValueError, match="must not contain duplicate units"):
        model.model_validate(payload)


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
    with pytest.raises(ValueError, match=r"volume delimiters|quote characters"):
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
    with pytest.raises(ValueError, match=r"PublishPort|single-line"):
        QuadletPod(publish_ports=[mapping])


def test_quadlet_pod_rejects_duplicate_host_ports() -> None:
    with pytest.raises(ValueError, match="duplicate host port 9999"):
        QuadletPod(publish_ports=["127.0.0.1:9999:8000", "127.0.0.1:9999:8001"])


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "logic\nWantedBy=default.target", "description": "safe"},
        {"name": "logic", "description": "swallow\\"},
        {"name": "logic", "description": "safe", "part_of": [r"safe\x25h.service"]},
        {"name": "logic", "description": "safe", "requires": ["safe.service injected.service"]},
    ],
)
def test_quadlet_target_rejects_directive_and_escape_injection(payload: dict[str, object]) -> None:
    with pytest.raises(ValueError, match=r"single-line|backslash|safe unit-name component"):
        QuadletTarget.model_validate(payload)


def test_animator_and_coven_unit_names_have_one_canonical_spelling() -> None:
    assert animator_service_stem("qwen") == "lychd-qwen"
    assert animator_service_unit("qwen") == "lychd-qwen.service"
    assert animator_target_unit("qwen") == "lychd-animator-qwen.target"
    assert coven_target_unit("logic") == "lychd-coven-logic.target"


@pytest.mark.parametrize(
    "arguments",
    [
        ["--secret=extension-token"],
        ["--secret", "extension-token"],
        ["--secret extension-token"],
        ["'--secret=extension-token'"],
        ['"--secret" "extension-token"'],
        ["--secret='extension-token'"],
        ["--replace --secret=extension-token"],
    ],
)
def test_quadlet_container_requires_typed_secret_arguments(arguments: list[str]) -> None:
    with pytest.raises(ValueError, match="Raw Podman arguments"):
        QuadletContainer(
            description="Extension secret policy",
            image="example/extension:latest",
            container_name="extension-secret-test",
            podman_args=arguments,
        )


@pytest.mark.parametrize(
    "spec",
    [
        "extension-token",
        "extension-token,type=mount,target=/run/secrets/token,mode=0400",
        "extension-token,type=env,target=EXTENSION_TOKEN",
    ],
)
def test_quadlet_container_keeps_supported_raw_arguments_with_typed_secrets(spec: str) -> None:
    arguments = ["--replace", "--ipc=host", "--ulimit=memlock=-1:-1"]
    container = QuadletContainer(
        description="Extension secret policy",
        image="example/extension:latest",
        container_name="extension-secret-test",
        podman_args=arguments,
        secrets=[spec],
    )
    assert container.podman_args == arguments
    assert container.secrets == [spec]


@pytest.mark.parametrize(
    "arguments",
    [
        ["--publish=0.0.0.0:19999:9999/udp"],
        ["--publish", "0.0.0.0:19999:9999/udp"],
        ["--publish 0.0.0.0:19999:9999/udp"],
        ['"--publish=0.0.0.0:19999:9999/udp"'],
        ["-p", "0.0.0.0:19999:9999/udp"],
        ["-p0.0.0.0:19999:9999/udp"],
        ["-dp0.0.0.0:19999:9999/udp"],
        ["-itp", "0.0.0.0:19999:9999/udp"],
        ["--publish-all"],
        ["--publish-all=false"],
        ["-P"],
        ["-dP"],
        ["-itP"],
        ["--network=host"],
        ["--network", "host"],
        ["--net=host"],
        ["--net host"],
        ["--volume=/etc:/etc:ro"],
        ["--tmpfs=/:rw"],
        ["--tmpfs=/run/secrets:rw,nosuid,nodev,noexec,mode=0755,size=1m"],
        ["--tmpfs", "/run/secrets:rw,nosuid,nodev,noexec,mode=0755,size=1m"],
        ["--user=0"],
        ["--future-option=enabled"],
        ["--replace=true"],
        ["--replace=false"],
        ["--ipc=container:other"],
        [" --replace"],
        ["--replace "],
        ["'--replace'"],
        ["--replace --ipc=host"],
        ["--tmpfs=/app/logs:rw,nosuid,nodev,noexec,mode=1777 --net=host"],
        [""],
    ],
)
def test_quadlet_container_rejects_unsupported_raw_arguments(arguments: list[str]) -> None:
    with pytest.raises(ValueError, match="Raw Podman arguments"):
        QuadletContainer(
            description="Bounded raw arguments",
            image="example/extension:latest",
            container_name="extension-raw-args",
            podman_args=arguments,
        )


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["--replace"],
        [
            "--ulimit=memlock=-1:-1",
            "--replace",
            "--tmpfs=/app/logs:rw,nosuid,nodev,noexec,mode=1777",
            "--ipc=host",
            "--replace",
        ],
    ],
)
def test_quadlet_container_preserves_supported_raw_values(arguments: list[str]) -> None:
    container = QuadletContainer(
        description="Bounded raw arguments",
        image="example/extension:latest",
        container_name="extension-raw-args",
        podman_args=arguments,
    )

    assert container.podman_args == arguments


@pytest.mark.parametrize(
    ("read_only", "secrets"),
    [
        (False, ["mounted_token"]),
        (True, []),
        (True, ["environment_token,type=env,target=TOKEN"]),
    ],
)
def test_secret_mount_tmpfs_requires_a_read_only_container_and_mounted_secret(
    *, read_only: bool, secrets: list[str]
) -> None:
    with pytest.raises(ValueError, match="Secret mount tmpfs requires"):
        QuadletContainer(
            description="Secret projection",
            image="example/runtime",
            container_name="secret-projection",
            read_only=read_only,
            secrets=secrets,
            secret_mount_tmpfs=True,
        )


@pytest.mark.parametrize("value", ["true", "/run/elsewhere:rw", 1])
def test_secret_mount_tmpfs_accepts_only_a_boolean(value: object) -> None:
    with pytest.raises(ValueError, match="valid boolean"):
        QuadletContainer.model_validate(
            {
                "description": "Secret projection",
                "image": "example/runtime",
                "container_name": "secret-projection",
                "read_only": True,
                "secrets": ["mounted_token"],
                "secret_mount_tmpfs": value,
            }
        )
