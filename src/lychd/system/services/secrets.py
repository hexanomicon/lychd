"""Podman secret-store gateway used during bind-time reconciliation.

This service intentionally wraps only the command surface LychD needs:
- check whether a secret exists
- create/replace a secret
- ensure a secret is present

It is used by the bind ritual so Codex/runes can stay reference-only
(`*_secret` names) while values live in Podman's secret backend.
"""

from __future__ import annotations

import shutil
import subprocess


class PodmanSecretStoreError(RuntimeError):
    """Raised when Podman secret operations fail in a domain-specific way."""


class PodmanSecretStore:
    """Minimal wrapper over rootless Podman secret management commands."""

    def __init__(self, podman_bin: str | None = None) -> None:
        """Resolve and validate Podman binary path."""
        resolved = podman_bin or shutil.which("podman")
        if resolved is None:
            msg = "Podman is required for secret provisioning but was not found on PATH."
            raise PodmanSecretStoreError(msg)
        self._podman = resolved

    def exists(self, name: str) -> bool:
        """Return True when a Podman secret already exists."""
        result = subprocess.run(  # noqa: S603
            [self._podman, "secret", "exists", name],
            check=False,
            capture_output=True,
            text=True,
        )
        return result.returncode == 0

    def create(self, name: str, value: str) -> None:
        """Create or replace a Podman secret from stdin.

        The value is streamed to podman via stdin and is never echoed by this
        service.
        """
        try:
            subprocess.run(  # noqa: S603
                [self._podman, "secret", "create", "--replace", name, "-"],
                input=value,
                text=True,
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            msg = f"Failed to create podman secret '{name}': {detail}"
            raise PodmanSecretStoreError(msg) from exc

    def ensure_present(self, name: str, value: str) -> bool:
        """Create a secret only when missing.

        Returns:
            ``True`` when the secret had to be created, ``False`` when it
            already existed.

        """
        if self.exists(name):
            return False
        self.create(name, value)
        return True
