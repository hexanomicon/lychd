"""Same-host snapshot custody, finite publication, restart and hostile path controls."""

from __future__ import annotations

import os
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from lychd.config.settings.observability import SnapshotSourceSettings
from lychd.domain.oculus.models import MAX_SNAPSHOT_BYTES, ComponentDefinition, SourceSnapshot
from lychd.system.services.oculus_snapshot import SnapshotFileReader, SnapshotFileWriter


def snapshot(generation: str = "generation-1", **fields: Any) -> SourceSnapshot:
    return SourceSnapshot(
        source_id="fixture.source",
        generation=generation,
        profile_id="fixture.profile",
        profile_revision="1",
        generated_at=datetime.now(UTC),
        components=(ComponentDefinition(key="fixture.service", label="Fixture service", kind="service"),),
        **fields,
    )


def reader(path: Path, **fields: Any) -> SnapshotFileReader:
    return SnapshotFileReader(
        (SnapshotSourceSettings(source_id="fixture.source", registrant_id="crypt:fixture", path=path, **fields),)
    )


def test_atomic_snapshot_survives_writer_close_and_replacement_generation(tmp_path: Path) -> None:
    root = tmp_path / "observations"
    with SnapshotFileWriter(root) as writer:
        writer.submit(snapshot())
    first = reader(root).read()[0]
    assert first.failure is None
    assert first.snapshot is not None
    assert first.snapshot.generation == "generation-1"
    assert root.stat().st_mode & 0o777 == 0o700
    assert (root / "snapshot.json").stat().st_mode & 0o777 == 0o600
    with SnapshotFileWriter(root) as restarted:
        restarted.submit(snapshot("generation-2"))
    assert reader(root, expected_generation="generation-1").read()[0].failure == "generation_mismatch"
    current = reader(root).read()[0]
    assert current.snapshot is not None
    assert current.snapshot.generation == "generation-2"


@pytest.mark.parametrize(
    "unsafe", ["symlink", "hardlink", "permissions", "directory", "oversize", "duplicate", "schema"]
)
def test_reader_rejects_unsafe_or_invalid_file(tmp_path: Path, unsafe: str) -> None:
    root = tmp_path / "observations"
    root.mkdir(mode=0o700)
    target = root / "snapshot.json"
    raw = snapshot().model_dump_json().encode()
    if unsafe == "symlink":
        sibling = tmp_path / "other"
        sibling.write_bytes(raw)
        target.symlink_to(sibling)
    elif unsafe == "directory":
        target.mkdir(mode=0o700)
    else:
        target.write_bytes(b" " * (MAX_SNAPSHOT_BYTES + 1) if unsafe == "oversize" else raw)
        target.chmod(0o644 if unsafe == "permissions" else 0o600)
        if unsafe == "hardlink":
            os.link(target, tmp_path / "alias")
        if unsafe == "duplicate":
            target.write_bytes(raw.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1'))
        if unsafe == "schema":
            target.write_bytes(raw.replace(b'"schema_version":1', b'"schema_version":999'))
    result = reader(root).read()[0]
    assert result.snapshot is None
    assert result.failure == (
        "oversize" if unsafe == "oversize" else "invalid" if unsafe in {"duplicate", "schema"} else "unsafe"
    )


@pytest.mark.parametrize("unsafe", ["git", "symlink_parent", "directory_permissions"])
def test_writer_and_reader_refuse_unsafe_source_roots(tmp_path: Path, unsafe: str) -> None:
    parent = tmp_path / "parent"
    parent.mkdir(mode=0o700)
    if unsafe == "git":
        (parent / ".git").write_text("gitdir: elsewhere")
    if unsafe == "symlink_parent":
        alias = tmp_path / "alias"
        alias.symlink_to(parent, target_is_directory=True)
        parent = alias
    root = parent / "observations"
    root.mkdir(mode=0o755 if unsafe == "directory_permissions" else 0o700)
    with pytest.raises((ValueError, OSError)):
        SnapshotFileWriter(root)
    assert reader(root).read()[0].failure == "unsafe"


def test_reader_reports_missing_and_stale_without_claiming_current(tmp_path: Path) -> None:
    root = tmp_path / "observations"
    assert reader(root).read()[0].failure == "unavailable"
    old = snapshot().model_copy(update={"generated_at": datetime.now(UTC) - timedelta(minutes=1)})
    with SnapshotFileWriter(root) as writer:
        writer.submit(old)
    result = reader(root).read()[0]
    assert result.failure == "stale"
    assert result.snapshot is not None
    assert result.snapshot.generated_at == old.generated_at


def test_queue_is_finite_and_close_does_not_wait_for_blocked_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    entered, release = threading.Event(), threading.Event()
    original = SnapshotFileWriter._write  # pyright: ignore[reportPrivateUsage] - inject blocked physical IO

    def blocked(self: SnapshotFileWriter, value: SourceSnapshot) -> None:
        entered.set()
        release.wait(2)
        original(self, value)

    monkeypatch.setattr(SnapshotFileWriter, "_write", blocked)
    writer = SnapshotFileWriter(tmp_path / "observations")
    writer.submit(snapshot())
    assert entered.wait(1)
    for _ in range(10):
        writer.submit(snapshot())
    assert writer._queue.qsize() <= 1  # pyright: ignore[reportPrivateUsage] - verify the bounded intake
    assert writer.dropped >= 9
    assert not writer.close(timeout=0)
    release.set()
    assert writer.close()
    current = reader(tmp_path / "observations").read()[0]
    assert current.snapshot is not None
    assert current.snapshot.coverage.dropped >= 9


def test_second_writer_refuses_without_changing_first(tmp_path: Path) -> None:
    root = tmp_path / "observations"
    with SnapshotFileWriter(root) as first:
        with pytest.raises(BlockingIOError):
            SnapshotFileWriter(root)
        first.submit(snapshot())
    assert reader(root).read()[0].failure is None
