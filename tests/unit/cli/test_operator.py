from __future__ import annotations

import json
from types import SimpleNamespace
from typing import TYPE_CHECKING

from click.testing import CliRunner

from lychd.cli.operator import logs, status
from lychd.system.operator import (
    InventoryItem,
    InventoryReport,
    JournalRead,
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
    read = JournalRead(
        target=OperatorTarget.SYSTEM,
        units=("lychd-vessel.service",),
        content="hello\n",
    )
    journal = mocker.Mock()
    journal.read.return_value = read
    services = SimpleNamespace(journal=journal)
    mocker.patch("lychd.cli.operator.build_operator_services", return_value=services)

    result = CliRunner().invoke(logs, ["--lines", "5"])

    assert result.exit_code == 0
    assert result.output == "hello\n"
