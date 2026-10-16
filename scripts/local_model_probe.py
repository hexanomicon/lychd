"""Qualify an explicit warm localhost model without installation or lifecycle authority."""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import sys
import time
from contextlib import redirect_stdout
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from typing import TYPE_CHECKING, Literal, cast
from urllib.parse import urlsplit
from uuid import uuid4

import click
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator
from pydantic_ai.models.wrapper import WrapperModel
from pydantic_ai.toolsets import FunctionToolset

from lychd.agents.context_limits import limit_model_requests
from lychd.agents.deps import LychDDeps, Sigil
from lychd.agents.factory import AgentForge, AgentSpec, build_agent
from lychd.domain.animation.errors import CapabilityUnavailable
from lychd.domain.animation.schemas import ConcurrencyIntent, GenerationProfile
from lychd.domain.animation.services.declarations import AnimatorDeclarations
from lychd.domain.animation.services.loader import AnimatorLoader
from lychd.domain.animation.services.registry import AnimatorRegistry
from lychd.domain.cortex.context import ContextOrchestrator
from lychd.domain.cortex.dispatcher import Dispatcher
from lychd.domain.cortex.leases import LeaseLedger
from lychd.extensions.builtin.animator.soulstones.vllm import VllmSoulstoneConfig
from lychd.extensions.builtin.animator.vllm.register import register
from lychd.extensions.context import ExtensionContext

if TYPE_CHECKING:
    from pydantic_ai.messages import ModelMessage, ModelResponse
    from pydantic_ai.models import Model, ModelRequestParameters
    from pydantic_ai.settings import ModelSettings
    from pydantic_ai.usage import UsageLimits

    from lychd.domain.orchestration.schema import TransitionPlan

_TEXT_MARKER = "cobalt-731"
_FINISH_REASON_MAX_LENGTH = 64


class ProbeProfile(BaseModel):
    """Explicit local-only input; no ambient provider or installation discovery."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    base_url: str
    model_id: str = Field(min_length=1, max_length=256)
    source_revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    context_tokens: int = Field(default=4096, ge=1024, le=32768)
    max_tokens: int = Field(default=256, ge=32, le=2048)
    deadline_seconds: float = Field(default=30, ge=1, le=120, allow_inf_nan=False)

    @field_validator("base_url")
    @classmethod
    def _local_endpoint(cls, value: str) -> str:
        target = urlsplit(value)
        if (
            value != value.strip()
            or not value.isprintable()
            or target.scheme != "http"
            or target.hostname not in {"127.0.0.1", "::1"}
            or target.port is None
            or target.port < 1
            or target.username is not None
            or target.password is not None
            or target.query
            or target.fragment
            or target.path.rstrip("/") != "/v1"
        ):
            msg = "Expected a literal-loopback HTTP /v1 endpoint with an explicit port and no credentials."
            raise ValueError(msg)
        return value.rstrip("/")

    @field_validator("model_id")
    @classmethod
    def _exact_model(cls, value: str) -> str:
        if value != value.strip() or not value.strip() or not value.isprintable():
            msg = "Expected an exact nonblank model id without control characters."
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def _input_budget(self) -> ProbeProfile:
        if self.max_tokens >= self.context_tokens:
            msg = "Output reservation must leave an input budget."
            raise ValueError(msg)
        return self


class RefusingTransitions:
    """The operator probe has no physical transition authority."""

    async def request_transition(self, target_capability_key: str, priority: int) -> TransitionPlan:
        """Refuse any accidental attempt to activate or change a runtime."""
        _ = target_capability_key, priority
        msg = "The local-model probe cannot request runtime transitions."
        raise RuntimeError(msg)


class ProbeResponseError(Exception):
    """A closed diagnostic code for an observed, inadmissible probe response."""


def _provider_finish_reason(response: ModelResponse) -> str | None:
    """Retain explicit bounded wire evidence rather than an SDK completion default."""
    value = (response.provider_details or {}).get("finish_reason")
    return value if isinstance(value, str) and len(value) <= _FINISH_REASON_MAX_LENGTH else None


class ProbeResponseModel(WrapperModel):
    """Record and check nonstreamed responses before Agent output or tool processing."""

    def __init__(self, wrapped: Model, *, model_id: str, responses: list[ModelResponse]) -> None:
        """Bind the exact declared identity and one case's received responses."""
        super().__init__(wrapped)
        self.expected_model_id = model_id
        self.responses = responses

    async def request(
        self,
        messages: list[ModelMessage],
        model_settings: ModelSettings | None,
        model_request_parameters: ModelRequestParameters,
    ) -> ModelResponse:
        """Reject unusable responses before they can invoke even the synthetic tool."""
        response = await self.wrapped.request(messages, model_settings, model_request_parameters)
        self.responses.append(response)
        wire_finish = _provider_finish_reason(response)
        admitted_finishes = {"stop": "stop", "tool_calls": "tool_call", "function_call": "tool_call"}
        if response.model_name != self.expected_model_id:
            code = "response_model_mismatch"
        elif response.finish_reason == "length" or wire_finish == "length":
            code = "output_limit"
        elif wire_finish is None or admitted_finishes.get(wire_finish) != response.finish_reason:
            code = "incomplete_response"
        else:
            return response
        raise ProbeResponseError(code)


def _registry(profile: ProbeProfile) -> AnimatorRegistry:
    context = ExtensionContext()
    register(context.registration_view("builtin:animator/vllm"))
    context.freeze()
    rune = VllmSoulstoneConfig(
        name="bootstrap-probe",
        base_url=profile.base_url,  # pyright: ignore[reportArgumentType] - Pydantic validates the explicit URL
        port=urlsplit(profile.base_url).port,
        served_model_id=profile.model_id,
        concurrency=ConcurrencyIntent(dedicated=False),
        generation=GenerationProfile(max_context=profile.context_tokens, max_tokens=profile.max_tokens, temperature=0),
    )
    stones, portals = AnimatorLoader(reserved_ports={}, core_secret_names=()).hydrate_all((rune,))
    registry = AnimatorRegistry(
        declarations=AnimatorDeclarations(soulstones=tuple(stones), portals=tuple(portals)),
        soulstone_registrations=context.soulstones.registrations,
    )
    registry.load(probe_readiness=False)
    return registry


def _refusal(registry: AnimatorRegistry | None, key: str) -> dict[str, object]:
    state = registry.get_capability_state(key) if registry is not None else None
    if state is None:
        return {"error_type": "capability_unsupported"}
    codes = {"down": "endpoint_unreachable", "inventory_invalid": "inventory_invalid", "model_missing": "model_missing"}
    return {"error_type": codes.get(state.health, "capability_unsupported"), "observed_phase": state.phase.value}


async def run_probe(profile: ProbeProfile) -> dict[str, object]:  # noqa: C901, PLR0915 - one two-case settlement with scoped tools
    """Settle two bounded synthetic cases; never manufacture a durable LychD Run."""
    started = time.monotonic()
    probe_id = f"operator-probe:{uuid4().hex}"
    key = f"bootstrap-probe:chat:{profile.model_id}"
    leases = LeaseLedger()
    cases: list[dict[str, object]] = []
    calls: list[str] = []
    registry: AnimatorRegistry | None = None
    tool_marker = secrets.token_hex(12)
    result: dict[str, object] = {
        "schema": "lychd-local-model-probe@1",
        "probe_id": probe_id,
        "started_at": datetime.now(UTC).isoformat(),
        "declared_profile": profile.model_dump(),
        "versions": {name: version(name) for name in ("lychd", "pydantic-ai-slim", "pydantic-graph")},
        "capability_key": key,
        "status": "failed",
        "stage": "registration",
        "cases": cases,
    }

    async def probe_echo(value: Literal["cobalt-731"]) -> str:
        """Return a fresh host marker for the exact public probe argument."""
        if calls:
            msg = "The probe permits one tool execution."
            raise ValueError(msg)
        calls.append(value)
        return tool_marker

    def toolset() -> FunctionToolset[LychDDeps]:
        tools: FunctionToolset[LychDDeps] = FunctionToolset(id="local-probe")
        tools.add_function(probe_echo)
        return tools

    forge = AgentForge({"local-probe": lambda spec: build_agent(spec, toolset_factories={"echo": toolset})})

    async def run_case(case: str, registry: AnimatorRegistry, dispatcher: Dispatcher) -> bool:
        result["stage"] = f"{case}:dispatch"
        case_started = time.monotonic()
        async with dispatcher.lease_grant(
            family="chat", capability_key=key, run_id=probe_id, requires_tools=case == "tool"
        ) as grant:
            result["inventory_matched_model_id"] = grant.spec.model_id
            result["registrant_id"] = grant.spec.registrant_id
            result["observed_phase"] = grant.state.phase.value
            model, limits = limit_model_requests(
                grant.model, context_window=profile.context_tokens, output_reserve=profile.max_tokens
            )
            limits = cast("UsageLimits", limits)  # a finite context_tokens always creates limits
            limits.request_limit = 2 if case == "tool" else 1
            limits.tool_calls_limit = 1 if case == "tool" else 0
            limits.total_tokens_limit = profile.context_tokens * 2
            spec = AgentSpec(
                name="local-probe",
                instructions_key=f"local-probe:{case}@1",
                instructions="Follow the synthetic acceptance task exactly. Give only the requested marker.",
                output_types=(str,),
                toolset_names=("echo",) if case == "tool" else (),
                retries=0,
                max_tokens=profile.max_tokens,
            )
            prompt = (
                "Call probe_echo exactly once with value='cobalt-731'. "
                "Then reply with exactly the marker returned by that tool, without any other text."
                if case == "tool"
                else f"Reply with exactly {_TEXT_MARKER}, without any other text."
            )
            deps = LychDDeps(
                sigil=Sigil(name="bootstrap-probe", scopes=frozenset()),
                grant=grant,
                dispatcher=dispatcher,
                orchestrator=RefusingTransitions(),
                context=ContextOrchestrator(registry=registry),
                run_id=probe_id,
                step_id=case,
                priority=50,
            )
            result["stage"] = f"{case}:inference"
            responses: list[ModelResponse] = []
            observed = ProbeResponseModel(cast("Model", model), model_id=profile.model_id, responses=responses)
            case_result: dict[str, object] = {"name": case, "passed": False}
            cases.append(case_result)
            try:
                answer = await forge.agent_for(spec).run(
                    prompt, deps=deps, model=observed, model_settings=grant.model_settings(), usage_limits=limits
                )
                expected = tool_marker if case == "tool" else _TEXT_MARKER
                passed = (
                    bool(responses)
                    and answer.output.strip() == expected
                    and (case != "tool" or calls == [_TEXT_MARKER])
                )
                case_result.update(passed=passed, requests=answer.usage.requests)
                if not passed:
                    result["error_type"] = "acceptance_failed"
                return passed
            finally:
                case_result.update(
                    response_model_ids=[str(item.model_name)[:256] for item in responses],
                    finish_reasons=[item.finish_reason for item in responses],
                    provider_finish_reasons=[_provider_finish_reason(item) for item in responses],
                    responses_received=len(responses),
                    input_tokens=sum(item.usage.input_tokens for item in responses),
                    output_tokens=sum(item.usage.output_tokens for item in responses),
                    seconds=round(time.monotonic() - case_started, 4),
                )

    try:
        async with asyncio.timeout(profile.deadline_seconds):
            registry = _registry(profile)
            dispatcher = Dispatcher(registry, leases=leases)
            for case in ("text", "tool"):
                if not await run_case(case, registry, dispatcher):
                    break
            else:
                result["status"] = "passed"
                result["stage"] = "complete"
    except TimeoutError:
        result["error_type"] = "deadline"
    except asyncio.CancelledError:
        result["error_type"] = "cancelled"
    except CapabilityUnavailable:
        result.update(_refusal(registry, key))
    except ProbeResponseError as exc:
        result["error_type"] = str(exc)
    except Exception as exc:  # noqa: BLE001 - settle the operator command without disclosing provider diagnostics
        result["error_type"] = type(exc).__name__
    result["tool_executions"] = len(calls)
    result["active_leases_after"] = len(leases.active())
    result["seconds"] = round(time.monotonic() - started, 4)
    if leases.active():
        result["status"] = "failed"
        result["error_type"] = "cleanup_failed"
    return result


@click.command()
@click.option("--base-url", required=True, help="Explicit http://127.0.0.1:PORT/v1 or http://[::1]:PORT/v1.")
@click.option("--model-id", required=True, help="Exact served model id; no fallback.")
@click.option("--source-revision", required=True, help="Declared checkout commit (40 lowercase hex characters).")
@click.option("--context-tokens", default=4096, type=int, show_default=True)
@click.option("--max-tokens", default=256, type=int, show_default=True)
@click.option("--deadline-seconds", default=30.0, type=float, show_default=True)
def cli(
    base_url: str, model_id: str, source_revision: str, context_tokens: int, max_tokens: int, deadline_seconds: float
) -> None:
    """Probe an already warm local vLLM service; JSON stdout, diagnostics stderr."""
    try:
        profile = ProbeProfile(
            base_url=base_url,
            model_id=model_id,
            source_revision=source_revision,
            context_tokens=context_tokens,
            max_tokens=max_tokens,
            deadline_seconds=deadline_seconds,
        )
    except ValidationError:
        click.echo(json.dumps({"status": "failed", "error_type": "invalid_profile"}))
        raise click.exceptions.Exit(2) from None
    probe_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with redirect_stdout(sys.stderr):
        receipt = asyncio.run(run_probe(profile))
    receipt["probe_sha256"] = probe_sha256
    click.echo(json.dumps(receipt, sort_keys=True))
    if receipt["status"] != "passed":
        raise click.exceptions.Exit(1)


if __name__ == "__main__":
    cli()
