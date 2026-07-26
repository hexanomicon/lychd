"""Tests for Linux-native atomic pathname operations."""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from lychd.system.atomic_paths import (
    rename_exchange,
    rename_exchange_at,
    rename_noreplace,
    rename_noreplace_at,
)


def test_rename_exchange_atomically_swaps_absolute_paths(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("source generation", encoding="utf-8")
    destination.write_text("destination generation", encoding="utf-8")
    source_inode = source.stat().st_ino
    destination_inode = destination.stat().st_ino

    rename_exchange(source, destination)

    assert source.read_text(encoding="utf-8") == "destination generation"
    assert destination.read_text(encoding="utf-8") == "source generation"
    assert source.stat().st_ino == destination_inode
    assert destination.stat().st_ino == source_inode


def test_rename_noreplace_moves_when_absolute_target_is_absent(
    tmp_path: Path,
) -> None:
    source = tmp_path / "staged"
    destination = tmp_path / "installed"
    source.write_text("new generation", encoding="utf-8")

    rename_noreplace(source, destination)

    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "new generation"


def test_descriptor_relative_operations_use_the_supplied_directories(
    tmp_path: Path,
) -> None:
    source_directory = tmp_path / "source-directory"
    destination_directory = tmp_path / "destination-directory"
    source_directory.mkdir()
    destination_directory.mkdir()
    (source_directory / "candidate").write_text("candidate", encoding="utf-8")
    (destination_directory / "incumbent").write_text("incumbent", encoding="utf-8")
    source_fd = os.open(source_directory, os.O_RDONLY | os.O_DIRECTORY)
    destination_fd = os.open(destination_directory, os.O_RDONLY | os.O_DIRECTORY)

    try:
        rename_exchange_at(
            "candidate",
            "incumbent",
            source_dir_fd=source_fd,
            destination_dir_fd=destination_fd,
        )
        (source_directory / "staged").write_text("staged", encoding="utf-8")
        rename_noreplace_at(
            "staged",
            "installed",
            source_dir_fd=source_fd,
            destination_dir_fd=destination_fd,
        )
    finally:
        os.close(source_fd)
        os.close(destination_fd)

    assert (source_directory / "candidate").read_text(encoding="utf-8") == "incumbent"
    assert (destination_directory / "incumbent").read_text(encoding="utf-8") == "candidate"
    assert not (source_directory / "staged").exists()
    assert (destination_directory / "installed").read_text(encoding="utf-8") == "staged"


def test_rename_noreplace_preserves_kernel_error_and_both_paths(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "destination"
    source.write_text("source", encoding="utf-8")
    destination.write_text("destination", encoding="utf-8")

    with pytest.raises(
        OSError,
        match=rf"\[Errno {errno.EEXIST}\]",
    ) as captured:
        rename_noreplace(source, destination)

    assert captured.value.errno == errno.EEXIST
    assert captured.value.filename == str(source)
    assert captured.value.filename2 == str(destination)
    assert source.read_text(encoding="utf-8") == "source"
    assert destination.read_text(encoding="utf-8") == "destination"


@pytest.mark.parametrize(
    "name",
    ["", ".", "..", "/absolute", "nested/name", "null\0name"],
)
def test_descriptor_relative_operations_reject_non_component_names(
    tmp_path: Path,
    name: str,
) -> None:
    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)

    try:
        with pytest.raises(ValueError, match="relative filename|null byte"):
            rename_noreplace_at(
                name,
                "destination",
                source_dir_fd=directory_fd,
                destination_dir_fd=directory_fd,
            )
    finally:
        os.close(directory_fd)
