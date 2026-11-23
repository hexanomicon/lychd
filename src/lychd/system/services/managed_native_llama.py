"""Bind one host-native llama.cpp service to its private Pod-side listener."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from lychd.system.host_tools import trusted_executable
from lychd.system.schemas import NativeRelayContainer, systemd_executable_token, validate_unit_name_component
from lychd.system.services.native_llama import native_llama_command
from lychd.system.unit_names import animator_service_unit, animator_target_unit, native_relay_stem

if TYPE_CHECKING:
    from lychd.config.settings.root import Settings
    from lychd.domain.animation.schemas import SoulstoneConfig


@dataclass(frozen=True, slots=True)
class ManagedNativeLlama:
    """Physical sources of the native process and its sole TCP-to-UDS bridge."""

    service_text: str
    relay: NativeRelayContainer


def _literal_argument(value: str) -> str:
    """Encode one systemd argv token, neutralizing specifiers and environment expansion."""
    if not value.isprintable() or value == ";":
        msg = "Native engine arguments must be printable single tokens without a command separator."
        raise ValueError(msg)
    escaped = value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%").replace("$", "$$")
    return f'"{escaped}"'


def compile_managed_native_llama(stone: SoulstoneConfig, settings: Settings) -> ManagedNativeLlama:
    """Compile mixed systemd ownership with no host TCP listener or ambient engine environment."""
    switching = settings.orchestration.switching
    if switching.actuator not in {"host-reactor", "systemd"}:
        msg = "Managed native Soulstones require the Linux systemd lifecycle owner."
        raise ValueError(msg)
    validate_unit_name_component(stone.name, field_name="native Soulstone")
    argv, port = native_llama_command(stone, switching, name=stone.name)
    env = trusted_executable("/usr/bin/env")
    if env is None:
        msg = "Managed native Soulstones require a trusted /usr/bin/env to isolate engine arguments."
        raise ValueError(msg)
    socket_dir = f"lychd-native-{stone.name}.endpoint"
    scratch_dir = f"lychd-native-{stone.name}.scratch"
    relay = native_relay_stem(stone.name)
    native = animator_service_unit(stone.name)
    target = animator_target_unit(stone.name)
    # A relative Unix socket resolves under the manager-created WorkingDirectory
    # and avoids the sockaddr_un length limit for long XDG runtime directories.
    argv[argv.index("--host") + 1] = "server.sock"
    command = " ".join(_literal_argument(value) for value in argv)
    service_text = "\n".join(
        (
            "[Unit]",
            f"Description=LychD native llama.cpp ({stone.name})",
            f"BindsTo=lychd-pod.service {target} {relay}.service",
            f"After=lychd-pod.service {target}",
            f"Before={relay}.service",
            "",
            "[Service]",
            "Type=exec",
            "UMask=0077",
            "NoNewPrivileges=yes",
            f"RuntimeDirectory={socket_dir} {scratch_dir}",
            "RuntimeDirectoryMode=0700",
            f"WorkingDirectory=%t/{socket_dir}",
            (
                f"ExecStart={systemd_executable_token(Path(env.path))} -i HOME=%t/{scratch_dir} "
                f"TMPDIR=%t/{scratch_dir} XDG_CACHE_HOME=%t/{scratch_dir} {command}"
            ),
            "",
        )
    )
    return ManagedNativeLlama(
        service_text=service_text,
        relay=NativeRelayContainer(
            socket_directory=socket_dir,
            description=f"LychD native llama.cpp listener ({stone.name})",
            image=settings.server.web.image,
            container_name=relay,
            pod="lychd.pod",
            user="%U",
            read_only=True,
            wants=[],
            binds_to=[native],
            after=["lychd-pod.service", native],
            wanted_by=[],
            restart_policy="no",
            exec=f"python -m lychd.system.services.native_socket_relay {port}",
        ),
    )
