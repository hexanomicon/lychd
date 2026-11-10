from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

from click.testing import CliRunner

from lychd.cli.operator import logs, status
from lychd.system.operator import (
    InventoryItem,
    InventoryReport,
    ObservationState,
    OperatorTarget,
    SystemSummary,
)

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def test_status_json_is_machine_readable(mocker: MockerFixture) -> None:
    report = InventoryReport(
        selector=OperatorTarget.SYSTEM,
        summary=SystemSummary.NOT_INITIALIZED,
        items=(
            InventoryItem(
                category=OperatorTarget.CONFIG,
                name="installation",
                state=ObservationState.ABSENT,
            ),
        ),
    )
    inventory = mocker.Mock()
    inventory.inspect.return_value = report
    services = SimpleNamespace(inventory=inventory)
    mocker.patch("lychd.cli.operator.build_operator_services", return_value=services)

    result = CliRunner().invoke(status, ["--json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == {
        "items": [
            {
                "attributes": {},
                "category": "config",
                "detail": "",
                "name": "installation",
                "state": "absent",
            }
        ],
        "selector": "system",
        "summary": "not-initialized",
        "warnings": [],
    }


def test_logs_command_emits_captured_content(mocker: MockerFixture) -> None:
    journal = mocker.Mock()
    journal.read.return_value = "hello\n"
    services = SimpleNamespace(journal=journal)
    mocker.patch("lychd.cli.operator.build_operator_services", return_value=services)

    result = CliRunner().invoke(logs, ["--lines", "5"])

    assert result.exit_code == 0
    assert result.output == "hello\n"


def test_deployment_projection_preserves_ordinary_inventory_boundary(mocker: MockerFixture) -> None:
    from lychd.system.services.deployment import DeploymentReport, DeploymentRequest

    report = DeploymentReport(DeploymentRequest("a" * 40), state="bound_inactive")
    inspect = mocker.patch("lychd.system.services.deployment.inspect_deployment", return_value=report)
    ordinary = mocker.patch("lychd.cli.operator.build_operator_services")
    result = CliRunner().invoke(status, ["--json", "--deployment-revision", "a" * 40])
    assert result.exit_code == 0
    assert json.loads(result.output)["next_action"] == "start"
    inspect.assert_called_once()
    ordinary.assert_not_called()


def test_deployment_requires_json_and_exact_identity_before_observation(mocker: MockerFixture) -> None:
    inspect = mocker.patch("lychd.system.services.deployment.inspect_deployment")
    for arguments in (
        ["--deployment-revision", "a" * 40],
        ["--json", "--deployment-revision", "moving"],
        ["--json", "--deployment-verify"],
        ["services", "--json", "--deployment-revision", "a" * 40],
    ):
        assert CliRunner().invoke(status, arguments).exit_code == 2
    inspect.assert_not_called()


def test_machine_failure_is_valid_secret_free_json(mocker: MockerFixture) -> None:
    mocker.patch("lychd.system.services.deployment.inspect_deployment", side_effect=ValueError("private credential"))
    result = CliRunner().invoke(status, ["--json", "--deployment-revision", "a" * 40])
    assert result.exit_code == 1
    assert "private credential" not in result.output
    assert json.loads(result.output)["next_action"] == "refuse"
