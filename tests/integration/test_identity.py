import pytest
from lychd.domain.cortex.dispatcher import HardwareTransitionRequired as HTR1
from lychd.domain.cortex.graph_runner import HardwareTransitionRequired as HTR2

@pytest.mark.asyncio
async def test_identity_crisis():
    print(f"DEBUG: HTR from dispatcher: {id(HTR1)}")
    print(f"DEBUG: HTR from graph_runner: {id(HTR2)}")
    assert HTR1 is HTR2
