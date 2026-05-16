import pytest

from lychd.domain.cortex import dispatcher, graph_runner


@pytest.mark.asyncio
async def test_graph_runner_reexports_canonical_transition_signal() -> None:
    assert dispatcher.HardwareTransitionRequired is graph_runner.HardwareTransitionRequired
