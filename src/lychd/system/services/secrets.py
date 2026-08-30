"""Podman secret-store gateway used during bind-time reconciliation.

This service intentionally wraps only the command surface LychD needs:
- check whether a secret exists
- create/replace a secret
- ensure a secret is present

It is used by the bind ritual so Codex/runes can stay reference-only
(`*_secret` names) while values live in Podman's secret backend.
"""

from __future__ import annotations

from lychd.system.operator.process import (
    InputProcessRunner,
    ProcessInvocationError,
    ProcessResult,
    SubprocessRunner,
)

_PODMAN_PROBE_TIMEOUT_SECONDS = 5.0
_PODMAN_CREATE_TIMEOUT_SECONDS = 30.0
_PODMAN_SECRET_ABSENT_EXIT = 1
_MAX_DIAGNOSTIC_CHARS = 4096


class PodmanSecretStoreError(RuntimeError):
    """Raised when Podman secret operations fail in a domain-specific way."""


class PodmanSecretStore:
    """Minimal wrapper over rootless Podman secret management commands."""

    def __init__(
        self,
        podman_bin: str,
        *,
        runner: InputProcessRunner | None = None,
    ) -> None:
        """Bind every command to the preflight-attested Podman executable."""
        self._podman = podman_bin
        self._runner = runner or SubprocessRunner()

    def exists(self, name: str) -> bool:
        """Return exact presence, distinguishing absence from probe failure."""
        result = self._run(
            (self._podman, "secret", "exists", name),
            timeout_s=_PODMAN_PROBE_TIMEOUT_SECONDS,
            operation=f"inspect Podman secret {name!r}",
        )
        if result.returncode == 0:
            return True
        if result.returncode == _PODMAN_SECRET_ABSENT_EXIT:
            return False
        detail = self._detail(result)
        msg = f"Could not inspect Podman secret {name!r}: {detail}"
        raise PodmanSecretStoreError(msg)

    def create(self, name: str, value: str) -> None:
        """Create or replace a Podman secret from stdin.

        The value is streamed to podman via stdin and is never echoed by this
        service.
        """
        result = self._create(name, value, replace=True)
        if result.returncode != 0:
            detail = self._detail(result)
            msg = f"Failed to create podman secret '{name}': {detail}"
            raise PodmanSecretStoreError(msg)

    def _create(
        self,
        name: str,
        value: str,
        *,
        replace: bool,
    ) -> ProcessResult:
        """Invoke Podman's create primitive without exposing secret material."""
        replace_args = ("--replace",) if replace else ()
        argv = (self._podman, "secret", "create", *replace_args, name, "-")
        try:
            return self._runner.run_with_input(
                argv,
                timeout_s=_PODMAN_CREATE_TIMEOUT_SECONDS,
                input_text=value,
            )
        except ProcessInvocationError as exc:
            msg = f"Failed to create Podman secret {name!r}: {exc}"
            raise PodmanSecretStoreError(msg) from exc

    def ensure_present(self, name: str, value: str) -> bool:
        """Atomically create a secret only when missing.

        Returns:
            ``True`` when the secret had to be created, ``False`` when it
            already existed or another process won the creation race.

        """
        if self.exists(name):
            return False
        result = self._create(name, value, replace=False)
        if result.returncode == 0:
            return True
        if self.exists(name):
            return False
        detail = self._detail(result)
        msg = f"Failed to create podman secret '{name}': {detail}"
        raise PodmanSecretStoreError(msg)

    def _run(
        self,
        argv: tuple[str, ...],
        *,
        timeout_s: float,
        operation: str,
    ) -> ProcessResult:
        """Run one no-stdin Podman probe and translate invocation failures."""
        try:
            return self._runner.run(argv, timeout_s=timeout_s)
        except ProcessInvocationError as exc:
            msg = f"Could not {operation}: {exc}"
            raise PodmanSecretStoreError(msg) from exc

    @staticmethod
    def _detail(result: ProcessResult) -> str:
        """Return one bounded diagnostic without ever including secret stdin."""
        raw = result.stderr.strip() or result.stdout.strip()
        return (raw or f"exit {result.returncode}")[:_MAX_DIAGNOSTIC_CHARS]
