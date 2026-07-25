"""Bounded systemd user-manager effects shared by host lifecycle commands."""

from __future__ import annotations

from lychd.system.operator.process import (
    ProcessInvocationError,
    ProcessRunner,
    SubprocessRunner,
)

_DAEMON_RELOAD_TIMEOUT_SECONDS = 30.0


class SystemdUserManagerError(RuntimeError):
    """A bounded user-manager operation could not complete successfully."""


class SystemdUserManager:
    """Apply allowlisted systemd user-manager operations without a shell."""

    def __init__(
        self,
        *,
        systemctl_bin: str,
        runner: ProcessRunner | None = None,
    ) -> None:
        """Bind one preflight-verified executable and an injectable process port."""
        self._systemctl = systemctl_bin
        self._runner = runner or SubprocessRunner()

    def daemon_reload(self) -> None:
        """Reload the user manager with a mandatory timeout and typed failure."""
        argv = (self._systemctl, "--user", "daemon-reload")
        try:
            result = self._runner.run(
                argv,
                timeout_s=_DAEMON_RELOAD_TIMEOUT_SECONDS,
            )
        except ProcessInvocationError as exc:
            message = f"systemd user daemon-reload could not complete: {exc}"
            raise SystemdUserManagerError(message) from exc
        if result.returncode != 0:
            detail = result.stderr.strip() or f"exit {result.returncode}"
            message = f"systemd user daemon-reload failed: {detail}"
            raise SystemdUserManagerError(message)


__all__ = ["SystemdUserManager", "SystemdUserManagerError"]
