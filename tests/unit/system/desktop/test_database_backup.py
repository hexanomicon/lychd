"""Desktop capture confines its temporary replication credential to the operator."""

from __future__ import annotations

from typing import TYPE_CHECKING

import click
import pytest
from pydantic import SecretStr

from lychd.config.settings import DatabaseSettings
from lychd.system.desktop import database_backup
from lychd.system.desktop.private import private_directory

if TYPE_CHECKING:
    from pathlib import Path


def test_registered_capture_cleans_password_after_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source = tmp_path / "cluster"
    destination = tmp_path / "backups"
    private_directory(destination)
    db = DatabaseSettings(user="test:user", password=SecretStr(r"a:b\c"))
    files: list[Path] = []

    def fail(pg_bin: Path, cluster: Path, target: Path, *, port: int, user: str, passfile: Path) -> Path:
        assert (pg_bin, cluster, target, user) == (tmp_path, source, destination, db.user)
        assert passfile.read_text() == rf"127.0.0.1:{port}:*:test\:user:a\:b\\c" + "\n"
        files.append(passfile)
        msg = "test interruption"
        raise OSError(msg)

    monkeypatch.setattr(database_backup, "capture", fail)
    with pytest.raises(click.ClickException, match="test interruption"):
        database_backup.capture_registered(tmp_path, source, destination, db)
    assert len(files) == 1
    assert not files[0].parent.exists()
