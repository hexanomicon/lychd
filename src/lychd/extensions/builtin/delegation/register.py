"""Register the built-in delegated-agent runtime."""

from __future__ import annotations

from lychd.extensions.context import ExtensionRegistrationContext
from lychd.extensions.delegation import DelegatedRuntimeDefinition


def register(context: ExtensionRegistrationContext) -> None:
    """Register the delivered process-local reference runtime."""
    from lychd.extensions.builtin.delegation.reference import ReferenceDelegatedAgentRuntime

    context.delegated_runtimes.add(
        DelegatedRuntimeDefinition(
            runtime_id="reference",
            display_name="Reference",
            limitations=(
                "Deterministic process-local demonstration only.",
                "Performs no model, filesystem, subprocess, or network work.",
            ),
            runtime_adapter=ReferenceDelegatedAgentRuntime(),
        )
    )
