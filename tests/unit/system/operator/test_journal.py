from __future__ import annotations

from typing import TYPE_CHECKING, cast

import pytest

from lychd.system.operator import (
    OperatorError,
    OperatorTarget,
    OperatorTargetResolver,
    OwnedUnit,
    OwnedUnitCatalog,
    ProcessResult,
)
from lychd.system.operator.journal import JournalService

if TYPE_CHECKING:
    from lychd.system.operator.inventory import OperatorInventoryService


class _Inventory:
    def __init__(self, catalog: OwnedUnitCatalog) -> None:
        self.catalog = catalog

    def owned_units(self) -> OwnedUnitCatalog:
        return self.catalog

    def declared_animators(self) -> tuple[object, ...]:
        return ()


class _Runner:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], float]] = []

    def run(self, argv: tuple[str, ...], *, timeout_s: float) -> ProcessResult:
        self.calls.append((argv, timeout_s))
        return ProcessResult(argv=argv, returncode=0, stdout="one line\n")


def test_logs_use_only_exact_receipted_units_and_bounded_argv() -> None:
    inventory = cast(
        "OperatorInventoryService",
        _Inventory(
            OwnedUnitCatalog(
                receipt_present=True,
                units=(
                    OwnedUnit(name="lychd-vessel.service", sources=()),
                    OwnedUnit(name="lychd-qwen.service", sources=()),
                ),
            )
        ),
    )
    runner = _Runner()
    service = JournalService(
        targets=OperatorTargetResolver(inventory),
        runner=runner,
        journalctl_bin="/usr/bin/journalctl",
    )

    read = service.read(lines=42)

    assert read.units == ("lychd-vessel.service", "lychd-qwen.service")
    assert read.content == "one line\n"
    assert runner.calls == [
        (
            (
                "/usr/bin/journalctl",
                "--user",
                "--no-pager",
                "--lines",
                "42",
                "--unit",
                "lychd-vessel.service",
                "--unit",
                "lychd-qwen.service",
            ),
            10.0,
        )
    ]


def test_logs_reject_config_target_without_calling_journal() -> None:
    inventory = cast(
        "OperatorInventoryService",
        _Inventory(OwnedUnitCatalog(receipt_present=False)),
    )
    runner = _Runner()
    service = JournalService(
        targets=OperatorTargetResolver(inventory),
        runner=runner,
        journalctl_bin="/usr/bin/journalctl",
    )

    with pytest.raises(OperatorError, match="no journal-backed runtime"):
        service.read(OperatorTarget.CONFIG)

    assert runner.calls == []
