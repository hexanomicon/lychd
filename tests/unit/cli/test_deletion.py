from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from click.testing import CliRunner

from lychd.cli.deletion import delete_installation
from lychd.system.constants import PATH_POSTGRESS_DATA_DIR
from lychd.system.services.lifecycle import (
    DeletionAction,
    DeletionActionKind,
    DeletionDisposition,
    DeletionOutcome,
    DeletionPlan,
    DeletionResult,
    DeletionStage,
    PrivilegedHandoff,
)

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.fixture
def plan(tmp_path: Path) -> DeletionPlan:
    return DeletionPlan(
        actions=(
            DeletionAction(
                DeletionStage.FILESYSTEM,
                DeletionDisposition.WOULD_APPLY,
                DeletionActionKind.REMOVE_TREE,
                str(tmp_path / "lychd-test"),
                "dedicated root is removable",
            ),
            DeletionAction(
                DeletionStage.PACKAGE,
                DeletionDisposition.PRESERVE,
                DeletionActionKind.PRESERVE_PACKAGE,
                "/source/lychd",
                "source checkout is outside deletion authority",
            ),
        )
    )


def _services(
    mocker: MockerFixture,
    *,
    plan: DeletionPlan,
    result: DeletionResult | None = None,
) -> MagicMock:
    services = mocker.MagicMock()
    services.planner.plan.return_value = plan
    services.executor.execute.return_value = result or DeletionResult(
        DeletionOutcome.COMPLETE,
        DeletionPlan(
            actions=(
                DeletionAction(
                    DeletionStage.PACKAGE,
                    DeletionDisposition.PRESERVE,
                    DeletionActionKind.PRESERVE_PACKAGE,
                    "/source/lychd",
                    "source checkout is outside deletion authority",
                ),
            )
        ),
        (DeletionStage.FILESYSTEM,),
        "safely owned resources removed",
    )
    mocker.patch(
        "lychd.cli.deletion.build_deletion_services",
        return_value=services,
    )
    return services


def test_del_dry_run_renders_every_stage_without_effects(
    mocker: MockerFixture,
    plan: DeletionPlan,
) -> None:
    services = _services(mocker, plan=plan)

    result = CliRunner().invoke(delete_installation, ["--dry-run"])

    assert result.exit_code == 0
    assert "DELETION PLAN" in result.output
    assert "FILESYSTEM" in result.output
    assert "WOULD APPLY" in result.output
    assert "HOST — paths outside the canonical XDG tiers" in result.output
    assert plan.actions[0].detail in result.output
    assert "PRESERVE" in result.output
    assert "No changes made." in result.output
    services.executor.execute.assert_not_called()


def test_del_reuses_xdg_trees_without_merging_safety_stages(
    mocker: MockerFixture,
) -> None:
    repeated_target = str(PATH_POSTGRESS_DATA_DIR)
    staged = DeletionPlan(
        actions=(
            DeletionAction(
                DeletionStage.STORAGE,
                DeletionDisposition.REQUIRES_ROOT,
                DeletionActionKind.UNMOUNT,
                repeated_target,
                "attested mount requires root",
            ),
            DeletionAction(
                DeletionStage.FILESYSTEM,
                DeletionDisposition.BLOCKED,
                DeletionActionKind.REMOVE_TREE,
                repeated_target,
                "mount boundary must settle first",
            ),
        )
    )
    _services(mocker, plan=staged)

    result = CliRunner().invoke(delete_installation, ["--dry-run"])

    assert result.exit_code == 2
    assert result.output.index("STORAGE") < result.output.index("FILESYSTEM")
    assert result.output.count("lychd/postgres/data") == 2
    assert result.output.count("CRYPT — ~/.local/share") == 2


def test_del_declined_confirmation_has_no_effects(
    mocker: MockerFixture,
    plan: DeletionPlan,
) -> None:
    services = _services(mocker, plan=plan)

    result = CliRunner().invoke(delete_installation, input="n\n")

    assert result.exit_code != 0
    assert "Permanently delete every safely owned resource" in result.output
    assert "Aborted!" in result.output
    services.executor.execute.assert_not_called()


def test_del_yes_executes_exact_rendered_fingerprint(
    mocker: MockerFixture,
    plan: DeletionPlan,
) -> None:
    services = _services(mocker, plan=plan)

    result = CliRunner().invoke(delete_installation, ["--yes"])

    assert result.exit_code == 0
    assert "DELETION COMPLETE" in result.output
    assert "Applied stages: filesystem" in result.output
    services.executor.execute.assert_called_once_with(plan.fingerprint)


def test_del_partial_root_handoff_is_copyable_and_nonzero(
    mocker: MockerFixture,
    plan: DeletionPlan,
) -> None:
    handoff = PrivilegedHandoff(
        argv=("sudo", "/usr/bin/umount", "--", "/srv/lychd/a path"),
        reason="unmount the exact checkpointed Phylactery",
    )
    handoff_plan = DeletionPlan(
        actions=(
            DeletionAction(
                DeletionStage.STORAGE,
                DeletionDisposition.REQUIRES_ROOT,
                DeletionActionKind.UNMOUNT,
                "/srv/lychd/a path",
                "attested mount requires root",
            ),
        ),
        handoffs=(handoff,),
    )
    services = _services(
        mocker,
        plan=plan,
        result=DeletionResult(
            DeletionOutcome.PARTIAL,
            handoff_plan,
            (DeletionStage.QUIESCE,),
            "privileged storage handoff required",
        ),
    )

    result = CliRunner().invoke(delete_installation, ["--yes"])

    assert result.exit_code == 2
    assert "DELETION PARTIAL" in result.output
    assert "ROOT HANDOFF" in result.output
    assert "sudo /usr/bin/umount -- '/srv/lychd/a path'" in result.output
    assert "invoke `lychd del` again" in result.output
    services.executor.execute.assert_called_once_with(plan.fingerprint)


def test_del_blocker_never_renders_an_executable_root_handoff(
    mocker: MockerFixture,
) -> None:
    """Known blockers keep later root work informational and non-copyable."""
    blocked = DeletionPlan(
        actions=(
            DeletionAction(
                DeletionStage.STORAGE,
                DeletionDisposition.REQUIRES_ROOT,
                DeletionActionKind.UNMOUNT,
                "/srv/lychd/data",
                "attested mount would require root",
            ),
            DeletionAction(
                DeletionStage.FILESYSTEM,
                DeletionDisposition.BLOCKED,
                DeletionActionKind.VERIFY_ROOT_AUTHORITY,
                "/srv/lychd/receipt",
                "root authority is missing",
            ),
        ),
    )
    _services(mocker, plan=blocked)

    result = CliRunner().invoke(delete_installation, ["--dry-run"])

    assert result.exit_code == 2
    assert "Root work is informational only until every blocker is cleared." in result.output
    assert "ROOT HANDOFF" not in result.output


def test_del_build_failure_is_a_cli_error(mocker: MockerFixture) -> None:
    mocker.patch(
        "lychd.cli.deletion.build_deletion_services",
        side_effect=ValueError("authority mismatch"),
    )

    result = CliRunner().invoke(delete_installation, ["--dry-run"])

    assert result.exit_code != 0
    assert "Error: authority mismatch" in result.output
