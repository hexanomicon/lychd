from __future__ import annotations

import pytest
from pydantic import ValidationError

from lychd.domain.orchestration.actuator import TransitionIntent, build_compensation_intent


def _forward_intent() -> TransitionIntent:
    return TransitionIntent(
        transition_id="a" * 32,
        config_generation="sha256:" + "b" * 64,
        target_animator="vision",
        evict_animators=("chat", "coding"),
        launch_animators=("vision",),
        expected_active_animators=("chat", "coding", "resident"),
    )


def test_compensation_is_exact_inverse_of_forward_world() -> None:
    forward = _forward_intent()

    compensation = build_compensation_intent(forward)

    assert compensation.operation == "compensation"
    assert compensation.rollback_of == forward.transition_id
    assert compensation.config_generation == forward.config_generation
    assert compensation.target_animator == forward.target_animator
    assert compensation.expected_active_animators == ("resident", "vision")
    assert compensation.evict_animators == ("vision",)
    assert compensation.launch_animators == ("chat", "coding")


def test_compensation_can_represent_inverse_of_pure_launch() -> None:
    forward = TransitionIntent(
        transition_id="c" * 32,
        config_generation="sha256:" + "d" * 64,
        target_animator="vision",
        launch_animators=("vision",),
    )

    compensation = build_compensation_intent(forward)

    assert compensation.evict_animators == ("vision",)
    assert compensation.launch_animators == ()
    assert compensation.expected_active_animators == ("vision",)


@pytest.mark.parametrize(
    "update",
    [
        {"operation": "forward", "rollback_of": "e" * 32},
        {"operation": "compensation", "rollback_of": None},
        {
            "operation": "compensation",
            "rollback_of": "e" * 32,
            "target_animator": "resident",
        },
    ],
)
def test_operation_specific_references_and_targets_fail_closed(update: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        TransitionIntent.model_validate({**_forward_intent().model_dump(), **update})


def test_compensation_cannot_be_inverted_recursively() -> None:
    with pytest.raises(ValueError, match="forward transition"):
        build_compensation_intent(build_compensation_intent(_forward_intent()))
