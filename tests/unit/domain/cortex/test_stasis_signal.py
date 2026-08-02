"""`_extract_signal`: stasis signals survive ExceptionGroup / cause-chain wrapping.

The old depth-1 `__cause__` walk missed the ExceptionGroup wrapping anyio task groups
can produce around a tool raised mid-stream. These pins guard the transitive search.
"""

from __future__ import annotations

import pytest

from lychd.domain.animation.errors import HardwareTransitionRequired
from lychd.domain.cortex.graph_runner import _extract_signal  # pyright: ignore[reportPrivateUsage]
from lychd.domain.cortex.runs import ConsentPending
from lychd.domain.delegation import DelegatedAgentJobRef, DelegatedAgentPending


def test_extract_finds_direct_signal() -> None:
    sig = HardwareTransitionRequired("chat:local", "local", None)
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
    sig = HardwareTransitionRequired("chat:local", "local", None)
    group = BaseExceptionGroup("mid-stream", [sig])
    assert _extract_signal(group, HardwareTransitionRequired) is sig


def test_extract_refuses_mixed_exception_group() -> None:
    sig = HardwareTransitionRequired("chat:local", "local", None)
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
