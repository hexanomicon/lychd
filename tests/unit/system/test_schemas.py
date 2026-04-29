from __future__ import annotations

from pathlib import Path

import pytest

from lychd.system.schemas import MountData


def test_mountdata_from_str_marks_non_symmetric_mount_as_not_mirrored() -> None:
    mount = MountData.from_str("/host/models:/models:ro,Z")

    assert mount.host_path == Path("/host/models")
    assert mount.container_path == Path("/models")
    assert mount.mirror is False


def test_mountdata_rejects_mirror_true_for_non_symmetric_paths() -> None:
    with pytest.raises(ValueError, match="mirror=True requires identical host_path and container_path"):
        MountData.model_validate(
            {
                "host_path": "/host/models",
                "container_path": "/models",
                "mirror": True,
                "options": ["ro", "Z"],
            }
        )
