"""Transaction tests for planned, journaled initialization."""

from __future__ import annotations

from pathlib import Path
from typing import cast
from unittest.mock import call

import pytest
from pytest_mock import MockerFixture

from lychd.system.services.lifecycle import (
    CreatedResources,
    InitializationExecutor,
    InitializationPlanner,
    InitializationRecorder,
    LifecycleAction,
    LifecycleDisposition,
    LifecycleError,
    LifecyclePlan,
    LifecycleReceiptStore,
    LifecycleResourceKind,
)


def _init_plan(
    *,
    directory: Path,
    receipt: Path,
    disposition: LifecycleDisposition,
) -> LifecyclePlan:
    return LifecyclePlan.combine(
        LifecyclePlan(
            actions=(
                LifecycleAction(
                    disposition,
                    LifecycleResourceKind.DIRECTORY,
                    str(directory),
                    "managed initialization directory",
                ),
                LifecycleAction(
                    disposition,
                    LifecycleResourceKind.RECEIPT,
                    str(receipt),
                    "owner-only initialization authority",
                ),
            )
        )
    )


def test_executor_consumes_exact_plan_and_verifies_convergence(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    """The rendered plan is rechecked and every reported creation is journaled."""
    directory = tmp_path / "codex"
    receipt_path = directory / ".lychd-lifecycle.json"
    approved = _init_plan(
        directory=directory,
        receipt=receipt_path,
        disposition=LifecycleDisposition.WOULD_CREATE,
    )
    preseal = LifecyclePlan.combine(
        LifecyclePlan(
            actions=(
                LifecycleAction(
                    LifecycleDisposition.PRESERVE,
                    LifecycleResourceKind.DIRECTORY,
                    str(directory),
                    "managed initialization directory",
                ),
                LifecycleAction(
                    LifecycleDisposition.WOULD_CREATE,
                    LifecycleResourceKind.RECEIPT,
                    str(receipt_path),
                    "owner-only initialization authority",
                ),
            )
        )
    )
    planner = mocker.MagicMock(spec=InitializationPlanner)
    planner.plan.side_effect = (approved, preseal)
    receipt = mocker.MagicMock(spec=LifecycleReceiptStore)
    receipt.path = receipt_path
    resources = CreatedResources(directories=(directory,))

    def effect(record: InitializationRecorder) -> CreatedResources:
        record(resources)
        return resources

    result = InitializationExecutor(
        planner=cast("InitializationPlanner", planner),
        receipt=cast("LifecycleReceiptStore", receipt),
    ).execute(approved, effects=(effect,))

    assert all(action.disposition is LifecycleDisposition.PRESERVE for action in result.actions)
    assert receipt.record.call_args_list == [
        call(resources),
        call(resources),
    ]
    receipt.seal_dedicated_roots.assert_called_once_with()


@pytest.mark.parametrize(
    ("preseal_disposition", "message"),
    [
        (LifecycleDisposition.WOULD_CREATE, "did not converge"),
        (LifecycleDisposition.BLOCKED, "Lifecycle plan is blocked"),
    ],
)
def test_executor_never_seals_a_nonconverged_or_blocked_plan(
    tmp_path: Path,
    mocker: MockerFixture,
    preseal_disposition: LifecycleDisposition,
    message: str,
) -> None:
    """A failed final read cannot grant later recursive deletion authority."""
    directory = tmp_path / "codex"
    receipt_path = directory / ".lychd-lifecycle.json"
    approved = _init_plan(
        directory=directory,
        receipt=receipt_path,
        disposition=LifecycleDisposition.WOULD_CREATE,
    )
    preseal = LifecyclePlan.combine(
        LifecyclePlan(
            actions=(
                LifecycleAction(
                    preseal_disposition,
                    LifecycleResourceKind.DIRECTORY,
                    str(directory),
                    "directory did not reach its required state",
                ),
                LifecycleAction(
                    LifecycleDisposition.WOULD_CREATE,
                    LifecycleResourceKind.RECEIPT,
                    str(receipt_path),
                    "pending dedicated-root attestation",
                ),
            )
        )
    )
    planner = mocker.MagicMock(spec=InitializationPlanner)
    planner.plan.side_effect = (approved, preseal)
    receipt = mocker.MagicMock(spec=LifecycleReceiptStore)
    receipt.path = receipt_path

    with pytest.raises(LifecycleError, match=message):
        InitializationExecutor(
            planner=cast("InitializationPlanner", planner),
            receipt=cast("LifecycleReceiptStore", receipt),
        ).execute(
            approved,
            effects=(lambda _record: CreatedResources(),),
        )

    receipt.seal_dedicated_roots.assert_not_called()


def test_executor_rejects_plan_drift_before_any_effect(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    """A preview whose observed generation changed is never executable."""
    directory = tmp_path / "codex"
    receipt_path = directory / ".lychd-lifecycle.json"
    approved = _init_plan(
        directory=directory,
        receipt=receipt_path,
        disposition=LifecycleDisposition.WOULD_CREATE,
    )
    drifted = LifecyclePlan.combine(
        approved,
        LifecyclePlan(
            actions=(
                LifecycleAction(
                    LifecycleDisposition.WOULD_CREATE,
                    LifecycleResourceKind.FILE,
                    str(directory / "unexpected"),
                    "new target appeared",
                ),
            )
        ),
    )
    planner = mocker.MagicMock(spec=InitializationPlanner)
    planner.plan.return_value = drifted
    receipt = mocker.MagicMock(spec=LifecycleReceiptStore)
    receipt.path = receipt_path
    effect = mocker.Mock()

    with pytest.raises(LifecycleError, match="state changed after planning"):
        InitializationExecutor(
            planner=cast("InitializationPlanner", planner),
            receipt=cast("LifecycleReceiptStore", receipt),
        ).execute(approved, effects=(effect,))

    effect.assert_not_called()
    receipt.record.assert_not_called()
    receipt.seal_dedicated_roots.assert_not_called()


def test_executor_rejects_unplanned_creation_before_receipting(
    tmp_path: Path,
    mocker: MockerFixture,
) -> None:
    """Effect callbacks cannot widen filesystem authority beyond the plan."""
    directory = tmp_path / "codex"
    receipt_path = directory / ".lychd-lifecycle.json"
    approved = _init_plan(
        directory=directory,
        receipt=receipt_path,
        disposition=LifecycleDisposition.WOULD_CREATE,
    )
    planner = mocker.MagicMock(spec=InitializationPlanner)
    planner.plan.return_value = approved
    receipt = mocker.MagicMock(spec=LifecycleReceiptStore)
    receipt.path = receipt_path
    unexpected = CreatedResources(files=(tmp_path / "outside",))

    def effect(record: InitializationRecorder) -> CreatedResources:
        record(unexpected)
        return unexpected

    with pytest.raises(LifecycleError, match="unplanned creation"):
        InitializationExecutor(
            planner=cast("InitializationPlanner", planner),
            receipt=cast("LifecycleReceiptStore", receipt),
        ).execute(approved, effects=(effect,))

    receipt.record.assert_not_called()
    receipt.seal_dedicated_roots.assert_not_called()
