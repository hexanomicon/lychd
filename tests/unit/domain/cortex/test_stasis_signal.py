"""`_extract_signal`: stasis signals survive ExceptionGroup / cause-chain wrapping.

The old depth-1 `__cause__` walk missed the ExceptionGroup wrapping anyio task groups
can produce around a tool raised mid-stream. These pins guard the transitive search.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.cortex.graph_runner import _extract_signal  # pyright: ignore[reportPrivateUsage]
from lychd.domain.cortex.runs import ConsentPending
from lychd.domain.delegation import DelegatedAgentJobRef, DelegatedAgentPending
from lychd.domain.intercom.native import PeerTaskPending, PeerTaskRef


@pytest.fixture(params=["hardware", "consent", "delegate", "peer"])
def wait_signal(request: pytest.FixtureRequest) -> Exception:
    if request.param == "hardware":
        return HardwareTransitionRequired("local:chat:model")
    if request.param == "consent":
        return ConsentPending("consent-1", "run-1", "effect")
    if request.param == "delegate":
        return DelegatedAgentPending(
            DelegatedAgentJobRef(job_id="job-1", request_id="request-1", run_id="run-1", runtime="inert")
        )
    return PeerTaskPending(
        PeerTaskRef(
            task_id=UUID(int=1),
            run_id="run-1",
            station="peer",
            request_id=UUID(int=2),
            binding_digest="a" * 64,
        )
    )


@pytest.mark.parametrize("shape", ["direct", "group", "explicit_wrapper", "mixed_first", "mixed_last"])
def test_extract_refuses_cleanup_failure_with_implicit_wait_context(wait_signal: Exception, shape: str) -> None:
    failure = RuntimeError("cleanup failed")

    def fail_cleanup() -> None:
        try:
            raise wait_signal
        finally:
            raise failure

    with pytest.raises(RuntimeError) as caught:
        fail_cleanup()

    assert caught.value is failure
    assert failure.__context__ is wait_signal
    assert failure.__cause__ is None
    candidate: BaseException = failure
    if shape == "group":
        candidate = ExceptionGroup("cleanup", [ExceptionGroup("inner", [failure])])
    elif shape == "explicit_wrapper":
        candidate = RuntimeError("wrapped cleanup")
        candidate.__cause__ = failure
    elif shape == "mixed_first":
        candidate = ExceptionGroup("mixed", [failure, wait_signal])
    elif shape == "mixed_last":
        candidate = ExceptionGroup("mixed", [wait_signal, failure])
    assert _extract_signal(candidate, type(wait_signal)) is None


def test_extract_preserves_explicit_wait_wrappers_inside_groups(wait_signal: Exception) -> None:
    wrapper = RuntimeError("explicit wait wrapper")
    wrapper.__cause__ = wait_signal
    group = ExceptionGroup("outer", [ExceptionGroup("inner", [wrapper])])
    assert _extract_signal(group, type(wait_signal)) is wait_signal


def test_extract_finds_direct_signal() -> None:
    sig = HardwareTransitionRequired("chat:local")
    assert _extract_signal(sig, HardwareTransitionRequired) is sig


def test_extract_walks_cause_chain() -> None:
    sig = ConsentPending("consent_1", "run_1", "request_coven_swap")
    wrapper = RuntimeError("wrapped")
    wrapper.__cause__ = sig
    assert _extract_signal(wrapper, ConsentPending) is sig


def test_extract_respects_suppressed_context() -> None:
    sig = ConsentPending("consent_1", "run_1", "request_coven_swap")

    def replace_signal() -> None:
        try:
            raise sig
        except ConsentPending:
            message = "replacement"
            raise RuntimeError(message) from None

    with pytest.raises(RuntimeError) as caught:
        replace_signal()

    replacement = caught.value
    assert replacement.__context__ is sig
    assert replacement.__suppress_context__ is True
    assert _extract_signal(replacement, ConsentPending) is None


def test_extract_unwraps_single_signal_exception_group() -> None:
    sig = HardwareTransitionRequired("chat:local")
    group = BaseExceptionGroup("mid-stream", [sig])
    assert _extract_signal(group, HardwareTransitionRequired) is sig


def test_extract_refuses_mixed_exception_group() -> None:
    sig = HardwareTransitionRequired("chat:local")
    group = BaseExceptionGroup("mid-stream", [ValueError("real failure"), sig])

    assert _extract_signal(group, HardwareTransitionRequired) is None


def test_extract_finds_nested_pure_delegated_agent_signal() -> None:
    sig = DelegatedAgentPending(
        DelegatedAgentJobRef(
            job_id="job-1",
            request_id="request-1",
            run_id="run-1",
            runtime="fake",
        )
    )
    group = BaseExceptionGroup("outer", [BaseExceptionGroup("mid-stream", [sig])])
    assert _extract_signal(group, DelegatedAgentPending) is sig


def test_extract_refuses_multiple_distinct_signals() -> None:
    first = ConsentPending("consent_1", "run_1", "request_coven_swap")
    second = ConsentPending("consent_2", "run_1", "request_coven_swap")

    assert _extract_signal(BaseExceptionGroup("ambiguous", [first, second]), ConsentPending) is None


def test_extract_returns_none_when_absent() -> None:
    assert _extract_signal(RuntimeError("plain"), ConsentPending) is None


def test_extract_is_cycle_safe() -> None:
    a = RuntimeError("a")
    b = RuntimeError("b")
    a.__cause__ = b
    b.__context__ = a  # deliberate cycle
    assert _extract_signal(a, ConsentPending) is None
