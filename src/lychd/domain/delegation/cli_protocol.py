"""Bounded official CLI protocols; launch intent is never containment evidence.

The host must provision fresh isolated homes, exclude ambient/project configuration,
resolve executable and roots without symlinks, admit every model request through the
Provider and Portal Gates, and enforce all ADR 09 limits before executing this intent.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import cast

from lychd.domain.delegation.cli_values import (
    CliLimits,
    CliRuntimeKind,
    CliWorkspace,
    require_cli_kind,
    reviewed_cli_version,
    validate_cli_model,
    validate_cli_path,
)
from lychd.domain.delegation.models import (
    DelegatedAgentJobRef,
    DelegatedAgentJobStatus,
    DelegatedAgentProfile,
    DelegatedAgentResult,
    DelegatedCliRequestV2,
    DelegatedRequest,
    decode_delegated_request,
    encode_delegated_request,
)

_MAX_PROMPT_BYTES = 1_048_576
_MAX_SESSION_ID_BYTES = 128


@dataclass(frozen=True, slots=True)
class CliLaunchSpec:
    """Immutable command intent passed exclusively to a trusted, refusing-by-default host.

    ``environment`` replaces the inherited environment. It intentionally contains no
    provider credential or auth file. A reviewed Gate bridge is still required; these
    flags and paths alone cannot make either CLI eligible for launch.
    """

    kind: CliRuntimeKind
    request: DelegatedRequest
    job: DelegatedAgentJobRef
    argv: tuple[str, ...]
    stdin: bytes
    workspace: CliWorkspace
    environment: tuple[tuple[str, str], ...]
    limits: CliLimits
    cli_version: str

    @property
    def digest(self) -> str:
        """Bind durable host evidence to the complete admitted command and limits."""
        payload = {
            "kind": self.kind.value,
            "cli_version": self.cli_version,
            "request": encode_delegated_request(self.request),
            "job": self.job.model_dump(mode="json"),
            "argv": self.argv,
            "stdin_sha256": sha256(self.stdin).hexdigest(),
            "workspace": asdict(self.workspace),
            "environment": self.environment,
            "limits": asdict(self.limits),
        }
        if isinstance(self.request, DelegatedCliRequestV2):
            payload["launch_codec"] = "lychd-delegated-cli-launch@2"
            return sha256(
                json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
            ).hexdigest()
        return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def build_cli_launch_spec(
    kind: CliRuntimeKind,
    *,
    executable: str,
    model: str,
    request: DelegatedRequest,
    job: DelegatedAgentJobRef,
    workspace: CliWorkspace,
    limits: CliLimits,
) -> CliLaunchSpec:
    """Build a literal one-shot command with no resume, shell, or fallback path."""
    require_cli_kind(kind)
    validate_cli_path(executable)
    validate_cli_model(model)
    if (
        request.runtime != kind.value
        or job.runtime != kind.value
        or request.request_id != job.request_id
        or request.run_id != job.run_id
        or request.profile != job.profile
    ):
        msg = "CLI request and job identity must agree exactly."
        raise ValueError(msg)
    prompt = request.prompt.encode("utf-8")
    if len(prompt) > _MAX_PROMPT_BYTES:
        msg = "CLI prompt exceeds the byte ceiling."
        raise ValueError(msg)
    if kind is CliRuntimeKind.CODEX:
        sandbox = "workspace-write" if request.profile is DelegatedAgentProfile.CANDIDATE else "read-only"
        argv = (
            executable,
            "exec",
            "--json",
            "--ephemeral",
            "--ignore-user-config",
            "--ignore-rules",
            "--config",
            'approval_policy="never"',
            "--sandbox",
            sandbox,
            "--model",
            model,
            "--color",
            "never",
            "--cd",
            workspace.workspace,
            "-",
        )
    else:
        argv = (
            executable,
            "--bare",
            "--print",
            "--output-format",
            "stream-json",
            "--verbose",
            "--no-session-persistence",
            "--permission-mode",
            "dontAsk",
            "--permission-prompts",
            "none",
            "--disable-slash-commands",
            "--strict-mcp-config",
            "--mcp-config",
            '{"mcpServers":{}}',
            "--settings",
            "{}",
            "--setting-sources",
            "",
            "--model",
            model,
        )
    environment = (
        ("HOME", f"{workspace.scratch}/home"),
        ("CODEX_HOME", f"{workspace.scratch}/codex"),
        ("CLAUDE_CONFIG_DIR", f"{workspace.scratch}/claude"),
        ("XDG_CONFIG_HOME", f"{workspace.scratch}/config"),
        ("XDG_CACHE_HOME", f"{workspace.scratch}/cache"),
        ("XDG_DATA_HOME", f"{workspace.scratch}/data"),
        ("TMPDIR", f"{workspace.scratch}/temporary"),
        ("LANG", "C.UTF-8"),
    )
    version = reviewed_cli_version(kind)
    return CliLaunchSpec(kind, request, job, argv, prompt, workspace, environment, limits, version)


def compile_cli_request(request: DelegatedCliRequestV2, job: DelegatedAgentJobRef) -> CliLaunchSpec:
    """Compile the exact retained official-one-shot@1 intent, without adapter defaults."""
    retained = decode_delegated_request(request)
    if not isinstance(retained, DelegatedCliRequestV2):
        msg = "A V2 CLI request is required."
        raise TypeError(msg)
    request = retained
    intent = request.cli_intent
    return build_cli_launch_spec(
        CliRuntimeKind(request.runtime),
        executable=intent.executable,
        model=intent.model,
        request=request,
        job=job,
        workspace=intent.workspace,
        limits=intent.limits,
    )


class CliProtocolError(ValueError):
    """Bounded output does not establish a complete supported protocol outcome."""


def _object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate JSON key."
            raise CliProtocolError(msg)
        result[key] = value
    return result


def _invalid_constant(value: str) -> object:
    del value
    raise CliProtocolError


def _records(stdout: bytes, limits: CliLimits) -> list[dict[str, object]]:
    if not stdout or not stdout.endswith(b"\n") or len(stdout) > limits.max_stdout_bytes:
        msg = "Missing or oversized CLI output."
        raise CliProtocolError(msg)
    records: list[dict[str, object]] = []
    for line in stdout.splitlines():
        if not line or len(line) > limits.max_record_bytes:
            msg = "Missing or oversized JSONL record."
            raise CliProtocolError(msg)
        value: object = json.loads(line.decode("utf-8"), object_pairs_hook=_object, parse_constant=_invalid_constant)
        if not isinstance(value, dict):
            raise CliProtocolError
        record = cast("dict[str, object]", value)
        if not isinstance(record.get("type"), str):
            msg = "JSONL event requires an object and type."
            raise CliProtocolError(msg)
        records.append(record)
    return records


def _agent_message(item: object) -> str | None:
    if not isinstance(item, dict):
        raise CliProtocolError
    record = cast("dict[str, object]", item)
    if record.get("type") != "agent_message":
        return None
    text = record.get("text")
    if not isinstance(text, str):
        raise CliProtocolError
    return text


def _codex(records: list[dict[str, object]]) -> tuple[bool, str | None]:
    started = False
    turn = False
    output: str | None = None
    for index, record in enumerate(records):
        kind = record["type"]
        if kind == "thread.started" and not started and isinstance(record.get("thread_id"), str):
            started = True
        elif kind == "turn.started" and started and not turn:
            turn = True
        elif kind == "item.completed" and turn:
            text = _agent_message(record.get("item"))
            if text is not None:
                output = text
        elif kind in {"turn.completed", "turn.failed"} and turn and index == len(records) - 1:
            if kind == "turn.completed" and output is None:
                raise CliProtocolError
            return kind == "turn.completed", output
        elif kind not in {"item.started", "item.updated", "error"} or not turn:
            raise CliProtocolError
    raise CliProtocolError


def _claude_session(record: dict[str, object]) -> str:
    session = record.get("session_id")
    if not isinstance(session, str) or not session or not session.isprintable():
        raise CliProtocolError
    if len(session.encode("utf-8")) > _MAX_SESSION_ID_BYTES:
        raise CliProtocolError
    return session


def _claude_message(record: dict[str, object]) -> None:
    """Admit the reviewed bare-print message subset, refusing unknown envelopes."""
    if record["type"] not in {"assistant", "user"} or record.get("error") is not None:
        raise CliProtocolError
    message = record.get("message")
    if not isinstance(message, dict):
        raise CliProtocolError
    fields = cast("dict[str, object]", message)
    if fields.get("role") != record["type"] or not isinstance(fields.get("content"), list):
        raise CliProtocolError


def _claude_result(record: dict[str, object]) -> tuple[bool, str | None]:
    if record["type"] != "result" or type(record.get("is_error")) is not bool:
        raise CliProtocolError
    subtype = record.get("subtype")
    if not isinstance(subtype, str):
        raise CliProtocolError
    if subtype == "success" and record["is_error"] is False:
        output = record.get("result")
        if not isinstance(output, str) or record.get("errors") or record.get("error"):
            raise CliProtocolError
        return True, output
    if (
        subtype
        in {"error_during_execution", "error_max_turns", "error_max_budget_usd", "error_max_structured_output_retries"}
        and record["is_error"] is True
    ):
        return False, None
    raise CliProtocolError


def _claude(records: list[dict[str, object]]) -> tuple[bool, str | None]:
    """Require one init/session and a single terminal after supported core messages.

    Additional CLI event variants are conservatively LOST until their envelopes and
    ordering have been reviewed. This is a bounded protocol subset, not a permissive
    SDK event collector.
    """
    initial = records[0]
    if initial["type"] != "system" or initial.get("subtype") != "init":
        raise CliProtocolError
    session = _claude_session(initial)
    for record in records[1:]:
        if _claude_session(record) != session:
            raise CliProtocolError
    for record in records[1:-1]:
        _claude_message(record)
    return _claude_result(records[-1])


def parse_cli_output(
    kind: CliRuntimeKind,
    stdout: bytes,
    *,
    job_id: str,
    exit_code: int,
    limits: CliLimits,
) -> DelegatedAgentResult:
    """Interpret provider claims only after the host proves whole-job containment.

    Missing, conflicting, truncated or oversized terminal evidence stays LOST. Raw
    stderr and foreign error strings are deliberately excluded from diagnostics.
    """
    try:
        require_cli_kind(kind)
        records = _records(stdout, limits)
        succeeded, output = _codex(records) if kind is CliRuntimeKind.CODEX else _claude(records)
        if succeeded and exit_code != 0:
            raise CliProtocolError
        if output is not None:
            output.encode("utf-8")
        return DelegatedAgentResult(
            job_id=job_id,
            status=DelegatedAgentJobStatus.SUCCEEDED if succeeded else DelegatedAgentJobStatus.FAILED,
            output=output if succeeded else None,
            error=None if succeeded else "CLI reported a failed turn.",
        )
    except (ValueError, UnicodeError, RecursionError):
        return DelegatedAgentResult(
            job_id=job_id,
            status=DelegatedAgentJobStatus.LOST,
            error="CLI output did not establish a complete bounded terminal outcome.",
        )
