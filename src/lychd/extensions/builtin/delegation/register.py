"""Register the built-in delegated-agent runtime catalogue."""

from __future__ import annotations

from lychd.extensions.context import ExtensionContext
from lychd.extensions.delegation import (
    DelegatedRuntimeCommand,
    DelegatedRuntimeDefinition,
    DelegatedRuntimeDelivery,
    DelegatedRuntimeSecurity,
    DelegatedRuntimeTransport,
)


def register(context: ExtensionContext) -> None:
    """Register one runnable reference and four fail-closed future adapters."""
    from lychd.extensions.builtin.delegation.reference import ReferenceDelegatedAgentRuntime

    context.delegated_runtimes.add(
        DelegatedRuntimeDefinition(
            runtime_id="reference",
            display_name="Reference",
            transport=DelegatedRuntimeTransport.REFERENCE,
            delivery=DelegatedRuntimeDelivery.AVAILABLE,
            security=DelegatedRuntimeSecurity(
                isolated_process=False,
                requires_nono=False,
                requires_provider_gate=False,
            ),
            limitations=(
                "Deterministic process-local demonstration only.",
                "Performs no model, filesystem, subprocess, or network work.",
            ),
            runtime_adapter=ReferenceDelegatedAgentRuntime(),
        )
    )
    context.delegated_runtimes.add(
        DelegatedRuntimeDefinition(
            runtime_id="codex-cli",
            display_name="Codex CLI",
            transport=DelegatedRuntimeTransport.CLI,
            delivery=DelegatedRuntimeDelivery.DECLARED_ONLY,
            security=_boxed_provider_security(),
            limitations=(
                "No effectful supervisor adapter is delivered.",
                "Provider Gate-compatible authentication is not delivered.",
                "Subscription or local user credentials are never projected into the coffin.",
            ),
            command=DelegatedRuntimeCommand(
                executable="codex",
                fixed_arguments=(
                    "exec",
                    "--json",
                    "--ephemeral",
                    "--ignore-user-config",
                    "--sandbox",
                    "read-only",
                    "-",
                ),
                prompt_via_stdin=True,
                evidence="Locally verified against codex 0.146.0 `codex exec --help`.",
            ),
        )
    )
    context.delegated_runtimes.add(
        DelegatedRuntimeDefinition(
            runtime_id="claude-code",
            display_name="Claude Code",
            transport=DelegatedRuntimeTransport.CLI,
            delivery=DelegatedRuntimeDelivery.DECLARED_ONLY,
            security=_boxed_provider_security(),
            limitations=(
                "No effectful supervisor adapter is delivered.",
                "Bare mode accepts API-key authentication only; no provider credential may enter the coffin.",
                "Provider Gate-compatible authentication is not delivered.",
            ),
            command=DelegatedRuntimeCommand(
                executable="claude",
                fixed_arguments=(
                    "--bare",
                    "--print",
                    "--output-format",
                    "stream-json",
                    "--no-session-persistence",
                ),
                prompt_via_stdin=True,
                evidence="Locally verified against Claude Code 2.1.220 `claude --help`.",
            ),
        )
    )
    context.delegated_runtimes.add(
        DelegatedRuntimeDefinition(
            runtime_id="opencode-go",
            display_name="OpenCode Go",
            transport=DelegatedRuntimeTransport.CLI,
            delivery=DelegatedRuntimeDelivery.DECLARED_ONLY,
            security=_boxed_provider_security(),
            limitations=(
                "The executable is absent from the audited host.",
                "No command contract or effectful supervisor adapter is delivered.",
                "Provider Gate-compatible authentication is not delivered.",
            ),
            command=DelegatedRuntimeCommand(
                executable="opencode",
                fixed_arguments=(),
                prompt_via_stdin=False,
                evidence="Only executable absence was locally verified; no CLI flags are claimed.",
            ),
        )
    )
    context.delegated_runtimes.add(
        DelegatedRuntimeDefinition(
            runtime_id="openrouter",
            display_name="OpenRouter",
            transport=DelegatedRuntimeTransport.PROVIDER_API,
            delivery=DelegatedRuntimeDelivery.DECLARED_ONLY,
            security=_boxed_provider_security(),
            limitations=(
                "OpenRouter is a provider route, not a standalone delegated-agent harness.",
                "No Provider Gate route, model policy, or agent adapter is delivered.",
            ),
        )
    )


def _boxed_provider_security() -> DelegatedRuntimeSecurity:
    return DelegatedRuntimeSecurity(
        isolated_process=True,
        requires_nono=True,
        requires_provider_gate=True,
    )
