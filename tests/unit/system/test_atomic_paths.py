"""Tests for Linux-native atomic pathname operations."""

from __future__ import annotations

import errno
import os
from pathlib import Path

import pytest

from lychd.system.atomic_paths import (
    rename_exchange_at,
    rename_noreplace_at,
)


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

    directory_fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with pytest.raises(
            OSError,
            match=rf"\[Errno {errno.EEXIST}\]",
        ) as captured:
            rename_noreplace_at(
                source.name,
                destination.name,
                source_dir_fd=directory_fd,
                destination_dir_fd=directory_fd,
            )
    finally:
        os.close(directory_fd)

    assert captured.value.errno == errno.EEXIST
    assert captured.value.filename == source.name
    assert captured.value.filename2 == destination.name
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
        with pytest.raises(ValueError, match=r"relative filename|null byte"):
            rename_noreplace_at(
                name,
                "destination",
                source_dir_fd=directory_fd,
                destination_dir_fd=directory_fd,
            )
    finally:
        os.close(directory_fd)
