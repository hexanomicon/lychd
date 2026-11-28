"""User-owned native PostgreSQL cluster and Vessel startup for personal desktops."""
# ruff: noqa: S603 -- fixed PostgreSQL commands, argv-only, using the operator's PostgreSQL installation.

from __future__ import annotations

import json
import os
import platform
import re
import shutil
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from typing import TYPE_CHECKING

import click

from lychd.system.constants import PATH_CACHE_ROOT, PATH_CRYPT_ROOT, PATH_LYCHD_TOML, PATH_POSTGRES_ROOT_DIR
from lychd.system.desktop.credentials import load_credentials, verify_credential_copy
from lychd.system.desktop.private import check_path, private_directory, publish_file, verify_private_directory
from lychd.system.desktop.volume_commands import volume
from lychd.system.desktop.volume_storage import cluster_path
from lychd.system.vessel_mode import require_native_user

if TYPE_CHECKING:
    from collections.abc import Generator

    import psycopg

    from lychd.config.settings import DatabaseSettings, Settings

_DATA = PATH_POSTGRES_ROOT_DIR / "native-data"
_MAJOR = "18"
_STOPPED = 3
_OWNER = "lychd-native-postgres-18-v1"


def _data() -> Path:
    """Resolve the selected storage once for this management command, including direct test calls."""
    ctx = click.get_current_context(silent=True)
    if ctx is None:
        return cluster_path(_DATA)
    if "desktop_cluster" not in ctx.meta:
        ctx.meta["desktop_cluster"] = cluster_path(_DATA)
    return Path(ctx.meta["desktop_cluster"])


def _require_postgres_version(binary: str) -> None:
    """Verify the selected server and reuse its version within the current CLI invocation."""
    ctx = click.get_current_context(silent=True)
    versions: dict[str, str] = ctx.meta.setdefault("desktop_pg_versions", {}) if ctx is not None else {}
    if binary not in versions:
        try:
            versions[binary] = subprocess.check_output([binary, "--version"], text=True).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            msg = f"Could not check PostgreSQL version with {binary}: {exc}"
            raise click.ClickException(msg) from exc
    if not re.match(rf"initdb \(PostgreSQL\) {_MAJOR}(?:\.|\s|$)", versions[binary]):
        msg = (
            f"Expected PostgreSQL {_MAJOR}, found {versions[binary]} at {binary}. "
            f"Set LYCHD_PG_BIN to a PostgreSQL {_MAJOR} bin directory."
        )
        raise click.ClickException(msg)


def postgres_program(name: str) -> str:
    """On macOS select one server installation, including Homebrew's keg-only PostgreSQL 18."""
    directory = os.environ.get("LYCHD_PG_BIN")
    if directory is None and sys.platform == "darwin":
        prefix = {"arm64": "/opt/homebrew", "x86_64": "/usr/local"}.get(platform.machine())
        brew = shutil.which("initdb", path=f"{prefix}/opt/postgresql@{_MAJOR}/bin") if prefix else None
        missing = f"PostgreSQL {_MAJOR} initdb is unavailable. Set LYCHD_PG_BIN to its bin directory."
        failure = click.ClickException(missing)
        for candidate in (shutil.which("initdb"), brew):
            if candidate is None:
                continue
            initdb = Path(candidate).resolve()
            try:
                _require_postgres_version(str(initdb))
            except click.ClickException as exc:
                failure = exc
            else:
                directory = str(initdb.parent)
                break
        else:
            raise failure
    binary = shutil.which(name, path=directory)
    if not binary:
        msg = f"PostgreSQL {_MAJOR} executable {name} is unavailable. Set LYCHD_PG_BIN to its bin directory."
        raise click.ClickException(msg)
    return binary


def desktop_settings(*, install: bool = False, admin: bool = False, allow_rotation: bool = False) -> Settings:
    from lychd.config.settings import Settings

    existing_cluster = _data().exists()
    load_credentials(
        administrative=admin,
        provision=install and not existing_cluster,
        required=install and existing_cluster,
        allow_rotation=allow_rotation,
    )
    settings = Settings()
    db = settings.server.database
    if db.profile != "postgres" or db.host not in {"127.0.0.1", "localhost"}:
        msg = "Desktop deployment requires the postgres profile and an IPv4 loopback database host."
        raise click.ClickException(msg)
    return settings


def _ctl(*args: str, check: bool = True) -> int:
    return subprocess.run([postgres_program("pg_ctl"), "-D", str(_data()), *args], check=check).returncode


def require_cluster() -> None:
    owner = _data() / ".lychd-desktop"
    check_path(owner)
    check_path(_data() / "PG_VERSION")
    if _data().is_symlink() or not owner.is_file() or owner.read_text(encoding="ascii") != _OWNER:
        msg = f"Unrecognized desktop database directory at {_data()}."
        raise click.ClickException(msg)
    version = _data() / "PG_VERSION"
    if not version.is_file() or version.read_text(encoding="ascii").strip() != _MAJOR:
        msg = f"Expected a dedicated PostgreSQL {_MAJOR} cluster at {_data()}."
        raise click.ClickException(msg)


def start_cluster(port: int) -> None:
    require_cluster()
    status_code = _ctl("status", check=False)
    if status_code == _STOPPED:  # pg_ctl indicates a stopped cluster.
        options = f"-c listen_addresses=127.0.0.1 -c unix_socket_directories= -p {port}"
        _ctl("-w", "-l", str(_data().parent / "native-postgres.log"), "-o", options, "start")
    elif status_code:
        msg = f"pg_ctl could not inspect the dedicated cluster (status {status_code})."
        raise click.ClickException(msg)


@contextmanager
def management_lock(*, wait: bool = False) -> Generator[None]:
    """Serialize management until the operating system closes this command's handle."""
    private_directory(PATH_POSTGRES_ROOT_DIR)
    path = PATH_POSTGRES_ROOT_DIR / ".desktop-management.lock"
    check_path(path)
    with path.open("a+b") as stream:
        try:
            if os.name == "nt":
                import msvcrt

                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_LOCK if wait else msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(stream.fileno(), fcntl.LOCK_EX if wait else fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            msg = "Another desktop management operation is active."
            raise click.ClickException(msg) from exc
        yield


class _DesktopCommand(click.Command):
    def invoke(self, ctx: click.Context) -> object:
        if sys.platform == "linux":
            if ctx.params.get("rebind_vault"):
                msg = "Rebinding OS vault credentials requires macOS or Windows."
                raise click.ClickException(msg)
            if ctx.params.get("method") == "apfs-clone":
                msg = "APFS cloning requires macOS."
                raise click.ClickException(msg)
        if self.name not in {"session", "status"}:
            ctx.with_resource(management_lock())
        return super().invoke(ctx)


@click.group()
@click.pass_context
def desktop(ctx: click.Context) -> None:
    """Manage the current user's native PostgreSQL cluster and foreground Vessel."""
    try:
        require_native_user()
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    if sys.platform == "linux" and ctx.invoked_subcommand in {
        "enable-login",
        "disable-login",
        "enable-vault",
        "volume",
    }:
        msg = f"Desktop {ctx.invoked_subcommand} requires a macOS or Windows provider."
        raise click.ClickException(msg)


desktop.command_class = _DesktopCommand
desktop.add_command(volume)


@desktop.command("reactor-prepare")
def reactor_prepare() -> None:
    """Prepare a private, read-only guest configuration and shared Animator inbox."""
    from lychd.system.desktop.reactor import prepare

    prepare()


@desktop.command("reactor-serve")
@click.option(
    "--listen", default="127.0.0.1", show_default=True, help="Host interface for authenticated model traffic."
)
def reactor_serve(listen: str) -> None:
    """Run the desktop host's Animator owner in the foreground."""
    from lychd.system.desktop.reactor import serve

    serve(listen)


def _prepare_installation() -> Settings:
    """Initialize native settings and the protected journal before starting any services."""
    check_path(PATH_LYCHD_TOML)
    check_path(_data())
    for root in (PATH_LYCHD_TOML.parent, PATH_CRYPT_ROOT, PATH_CACHE_ROOT):
        private_directory(root)
    private_directory(PATH_POSTGRES_ROOT_DIR)
    if not PATH_LYCHD_TOML.exists():
        native_state = json.dumps(str(PATH_POSTGRES_ROOT_DIR.parent / "native-runtimes"), ensure_ascii=False)
        content = (
            '[server.database]\nhost = "127.0.0.1"\nport = 55432\n'
            f'\n[orchestration.switching]\nactuator = "native-process"\nnative_state_dir = {native_state}\n'
        )
        publish_file(PATH_LYCHD_TOML, content.encode("utf-8"))
    settings = desktop_settings(install=True, admin=True)
    switching = settings.orchestration.switching
    directory = switching.native_state_dir
    if switching.actuator != "native-process" or directory is None:
        msg = "Desktop settings must select native-process and an absolute native_state_dir."
        raise click.ClickException(msg)
    if directory != PATH_POSTGRES_ROOT_DIR.parent / "native-runtimes" and directory.exists():
        # An explicit existing directory belongs to the operator. Validate it without changing its ACL.
        verify_private_directory(directory)
    else:
        private_directory(directory)
    return settings


def _initialize_cluster(binary: str, user: str, password: str) -> None:
    """Publish the dedicated cluster only after initdb and its ownership marker complete."""
    with TemporaryDirectory(prefix=".native-install-", dir=_data().parent) as directory:
        staged = Path(directory) / "cluster"
        with NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete_on_close=False) as secret_file:
            secret_file.write(password + "\n")
            secret_file.close()
            subprocess.run(
                [
                    binary,
                    "-D",
                    str(staged),
                    "-U",
                    user,
                    "--auth=scram-sha-256",
                    "--encoding=UTF8",
                    "-c",
                    "unix_socket_directories=",
                    f"--pwfile={secret_file.name}",
                ],
                check=True,
            )
        (staged / ".lychd-desktop").write_text(_OWNER, encoding="ascii")
        if _data().exists():
            raise FileExistsError(_data())
        staged.rename(_data())


@desktop.command()
def install() -> None:
    """Initialize or upgrade the dedicated database using installed PostgreSQL 18 and pgvector."""
    import psycopg
    from psycopg import sql

    from lychd.db.bootstrap import bootstrap_database
    from lychd.system.desktop.login import read_registration
    from lychd.system.desktop.volume_cluster import bind_installation

    read_registration()
    binary = postgres_program("initdb")
    _require_postgres_version(binary)
    settings = _prepare_installation()
    db = settings.server.database
    if db.password is None:
        msg = "The PostgreSQL administrative credential is unavailable."
        raise click.ClickException(msg)
    password = db.password.get_secret_value()
    if not _data().exists():
        _initialize_cluster(binary, db.user, password)
    start_cluster(db.port)
    bind_installation(_DATA, db, initialize=True)
    with psycopg.connect(
        host="127.0.0.1",
        hostaddr="127.0.0.1",
        port=db.port,
        user=db.user,
        password=password,
        dbname="postgres",
        autocommit=True,
    ) as conn:
        location = conn.execute("SHOW data_directory").fetchone()
        if location is None or not _data().samefile(location[0]):
            msg = "The configured port belongs to a different PostgreSQL cluster."
            raise click.ClickException(msg)
        if not conn.execute("SELECT 1 FROM pg_available_extensions WHERE name = 'vector'").fetchone():
            msg = "Install pgvector for this PostgreSQL installation, then repeat desktop install."
            raise click.ClickException(msg)
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db.database,)).fetchone():
            conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db.database)))
    with _exclusive_cluster(db):
        bootstrap_database(settings)
    click.echo("Desktop database initialized and runtime database authority verified.")


@desktop.command()
def start() -> None:
    """Start the dedicated PostgreSQL cluster."""
    start_cluster(desktop_settings().server.database.port)


@contextmanager
def _exclusive_cluster(db: DatabaseSettings) -> Generator[psycopg.Connection[tuple[object, ...]]]:
    """Fence bootstrap and shutdown against an active Vessel in the verified dedicated database."""
    import psycopg

    from lychd.interface.vessel_owner import VESSEL_LOCK_CLASS, VESSEL_LOCK_KEY

    if db.password is None:
        msg = "An administrator credential is required to verify the desktop database."
        raise click.ClickException(msg)
    connection = psycopg.connect(
        host="127.0.0.1",
        hostaddr="127.0.0.1",
        port=db.port,
        user=db.user,
        password=db.password.get_secret_value(),
        dbname=db.database,
        connect_timeout=5,
        autocommit=True,
    )
    try:
        location = connection.execute("SHOW data_directory").fetchone()
        if not location or not _data().samefile(location[0]):
            msg = "Configured database endpoint does not belong to the dedicated cluster."
            raise click.ClickException(msg)
        held = connection.execute(
            "SELECT pg_try_advisory_lock(%s::integer, %s::integer)", (VESSEL_LOCK_CLASS, VESSEL_LOCK_KEY)
        ).fetchone()
        if held != (True,):
            msg = "The Vessel is active. Run lychd stop before modifying the desktop database."
            raise click.ClickException(msg)
        yield connection
    finally:
        connection.close()


def stop_cluster(*, unregister: bool = False) -> None:
    from lychd.system.desktop.login import disable

    require_cluster()
    if _ctl("status", check=False) == _STOPPED:
        if unregister:
            disable()
        return
    with _exclusive_cluster(desktop_settings(admin=True).server.database):
        if unregister:
            disable()
        _ctl("-w", "-m", "fast", "stop")


@desktop.command()
def stop() -> None:
    """Stop the dedicated PostgreSQL cluster while preserving all data."""
    stop_cluster()


@desktop.command()
def status() -> None:
    """Report the running state of the dedicated PostgreSQL cluster."""
    require_cluster()
    raise click.exceptions.Exit(_ctl("status", check=False))


@desktop.command()
def session() -> None:
    """Start PostgreSQL and run the Vessel in the foreground for this login."""
    from lychd.__main__ import cli
    from lychd.system.desktop.login import load_environment

    with management_lock(wait=True):
        if sys.platform != "linux":
            load_environment()
        start_cluster(desktop_settings().server.database.port)
    cli.main(args=["start"], standalone_mode=False)


@desktop.command()
def enable_login() -> None:
    """Register the installed Python environment to start a desktop session at user login."""
    from lychd.system.desktop.login import enable

    require_cluster()
    enable()


@desktop.command()
def disable_login() -> None:
    """Remove the current user's LychD login registration, retaining settings and data."""
    from lychd.system.desktop.login import disable

    disable()


@desktop.command()
@click.option("--engine", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--model", type=click.Path(exists=True, dir_okay=False, path_type=Path), required=True)
@click.option("--port", type=click.IntRange(1, 65535), default=8081, show_default=True)
def configure_model(engine: Path, model: Path, port: int) -> None:
    """Bind browser chat to an installed llama-server and a local GGUF."""
    from lychd.system.desktop.model import configure

    configure(engine, model, port)
    click.echo("Configured personal:chat:personal-model for Bridge revision 2. Restart the Vessel to apply.")


@desktop.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False, path_type=Path))
def verify_credential_backup(directory: Path) -> None:
    """Compare a private backup with all generated desktop credentials."""
    try:
        verify_credential_copy(directory.absolute())
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo("All five generated credentials match the private backup.")


@desktop.command()
@click.argument("backup", type=click.Path(exists=True, file_okay=False, path_type=Path))
def enable_vault(backup: Path) -> None:
    """Move generated credentials into OS custody after verifying an independent recovery copy."""
    from lychd.system.desktop.credentials import use_os_vault

    try:
        use_os_vault(backup.absolute())
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo("OS vault enabled and all five credentials read back against the independent backup.")


@desktop.command()
@click.argument("backup", type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--rebind-vault", is_flag=True, help="Re-seal verified inaccessible vault credentials in this account.")
def recover_credentials(backup: Path, *, rebind_vault: bool) -> None:
    """Restore missing generated credentials from the operator's private recovery copy."""
    from lychd.system.desktop.credentials import restore_credentials

    try:
        restore_credentials(backup.absolute(), rebind_vault=rebind_vault)
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo("All generated credentials verified. The dedicated database can now be checked with desktop install.")


@desktop.command()
@click.option("--recovery-directory", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
def rotate_runtime_password(recovery_directory: Path) -> None:
    """Rotate the managed runtime DB role offline and verify an independent new recovery set."""
    from lychd.system.desktop.password_rotation import rotate

    require_cluster()
    settings = desktop_settings(admin=True, allow_rotation=True).server.database
    if (PATH_POSTGRES_ROOT_DIR / "desktop-credentials" / "pending-runtime-rotation.json").exists():
        # After a reboot the journal fences ordinary startup. Resume only the dedicated database.
        start_cluster(settings.port)
    try:
        with _exclusive_cluster(settings) as owner:
            rotate(settings, owner, recovery_directory.absolute())
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo("Runtime role rotated, old sessions closed and independent recovery copy verified.")


@desktop.command()
def uninstall() -> None:
    """Remove login integration and stop the dedicated database, preserving settings and data."""
    if sys.platform == "linux":
        stop_cluster()
        click.echo("Database stopped. Settings, credentials and data were retained.")
    else:
        stop_cluster(unregister=True)
        click.echo("Login service removed and database stopped. Settings, credentials and data were retained.")


@desktop.command()
@click.option("--destination", required=True, type=click.Path(exists=True, file_okay=False, path_type=Path))
@click.option("--method", type=click.Choice(["stream", "apfs-clone"]), default="stream", show_default=True)
def backup(destination: Path, method: str) -> None:
    """Capture the running desktop database into a fresh, verified offline copy."""
    from lychd.system.desktop.database_backup import capture_registered

    require_cluster()
    db = desktop_settings(admin=True).server.database
    if method == "apfs-clone":
        from lychd.system.desktop.apfs_clone import clone_database

        try:
            output = clone_database(
                _data(),
                destination.absolute(),
                db,
                postgres_program("pg_controldata"),
                stop_cluster,
                lambda: start_cluster(db.port),
            )
        except (OSError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc
    else:
        directory = Path(postgres_program("pg_basebackup")).absolute().parent
        output = capture_registered(directory, _data(), destination.absolute(), db)
    click.echo(f"Verified PostgreSQL backup: {output}")
