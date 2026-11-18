"""Register and remove only the desktop login service created by this installation."""

# ruff: noqa: S603 -- system executables, fixed commands, argument arrays.
from __future__ import annotations

import json
import os
import plistlib
import secrets
import subprocess
import sys
from pathlib import Path

import click

from lychd.system.constants import PATH_POSTGRES_ROOT_DIR
from lychd.system.desktop.private import check_path, private_directory, publish_file, verify_private_file

_LABEL = "org.lychd.vessel"
_PROFILE = PATH_POSTGRES_ROOT_DIR / "desktop-login" / "registration.json"
_KEYS = (
    "LYCHD_PG_BIN",
    "LYCHD_RUNTIME_DB_PASSWORD_FILE",
    "LYCHD_APP_SECRET_KEY_FILE",
    "LYCHD_LOCAL_ACCESS_PASSWORD_FILE",
)


def read_registration() -> dict[str, str]:
    """Check the recorded login owner without changing files or contacting the service manager."""
    check_path(_PROFILE)
    if not _PROFILE.exists():
        return {}
    verify_private_file(_PROFILE)
    values = json.loads(_PROFILE.read_text(encoding="utf-8"))
    if values.get("interpreter") != sys.executable or not values.get("identifier"):
        msg = (
            "The login registration belongs to another installation. Disable login with its original interpreter first."
        )
        raise click.ClickException(msg)
    if "python_mode" in values and values["python_mode"] != "isolated":
        msg = "The login registration has an unrecognized Python invocation."
        raise click.ClickException(msg)
    return values


def _create_registration() -> None:
    """Publish the identity and exact execution mode before contacting the OS."""
    from lychd.system.desktop import postgres_program

    private_directory(_PROFILE.parent)
    values = {key: os.environ[key] for key in _KEYS if key in os.environ}
    if any(os.environ.get(key.removesuffix("_FILE")) for key in _KEYS[1:]):
        msg = "Login registration requires generated credentials or explicit runtime credential file references."
        raise click.ClickException(msg)
    values.update(
        LYCHD_PG_BIN=str(Path(postgres_program("pg_ctl")).resolve().parent),
        interpreter=sys.executable,
        identifier=secrets.token_hex(20),
        python_mode="isolated",
    )
    publish_file(_PROFILE, json.dumps(values).encode("utf-8"))


def _arguments(registration: dict[str, str]) -> list[str]:
    module = ["-m", "lychd.system.desktop", "session"]
    return ["-I", "-B", *module] if registration.get("python_mode") == "isolated" else module


def load_environment() -> None:
    """Recover the executable directory and runtime credential files for this login."""
    values = read_registration()
    for key in _KEYS:
        if key in values:
            os.environ.setdefault(key, values[key])


def _plist() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{_LABEL}.plist"


def _windows(registration: dict[str, str], *, remove: bool) -> None:
    binary = Path(os.environ["SYSTEMROOT"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    script = """
$ErrorActionPreference='Stop'
$u=[Security.Principal.WindowsIdentity]::GetCurrent()
$n='LychD-Vessel-'+$u.User.Value
$d='LychD '+$env:LYCHD_LOGIN_IDENTIFIER
$x=$env:LYCHD_LOGIN_INTERPRETER
$argsText=$env:LYCHD_LOGIN_ARGUMENTS
function UserSid($name) {
    if ($name -match '^S-1-') {return $name}
    return ([Security.Principal.NTAccount]::new($name)).Translate([Security.Principal.SecurityIdentifier]).Value
}
function Check($task) {
    $a=@($task.Actions)
    $t=@($task.Triggers)
    if ($task.Description -cne $d -or $task.TaskPath -ne '\\' -or $task.TaskName -ne $n -or
        $a.Count -ne 1 -or $a[0].CimClass.CimClassName -ne 'MSFT_TaskExecAction' -or
        [IO.Path]::GetFullPath($a[0].Execute) -ne [IO.Path]::GetFullPath($x) -or
        $a[0].Arguments -cne $argsText -or $a[0].WorkingDirectory -or
        (UserSid $task.Principal.UserId) -ne $u.User.Value -or $task.Principal.LogonType -ne 'Interactive' -or
        $task.Principal.RunLevel -ne 'Limited' -or $t.Count -ne 1 -or
        $t[0].CimClass.CimClassName -ne 'MSFT_TaskLogonTrigger' -or (UserSid $t[0].UserId) -ne $u.User.Value) {
        throw 'Preserved unrecognized scheduled task'
    }
}
$existing=@(Get-ScheduledTask -TaskPath '\\' | Where-Object TaskName -eq $n)
if ($existing.Count) {
    Check $existing[0]
    if ($env:LYCHD_LOGIN_REMOVE -eq '1') {
        if($existing[0].State -eq 'Running'){throw 'Run lychd stop before removing the live login service'}
        Unregister-ScheduledTask -TaskPath '\\' -TaskName $n -Confirm:$false
    }
} elseif ($env:LYCHD_LOGIN_REMOVE -ne '1') {
    $a=New-ScheduledTaskAction -Execute $x -Argument $argsText
    $t=New-ScheduledTaskTrigger -AtLogOn -User $u.Name
    $p=New-ScheduledTaskPrincipal -UserId $u.Name -LogonType Interactive -RunLevel Limited
    $s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName $n -TaskPath '\\' -Description $d -Action $a -Trigger $t -Settings $s -Principal $p | Out-Null
    Check (Get-ScheduledTask -TaskPath '\\' -TaskName $n)
}
"""
    subprocess.run(
        [binary, "-NoProfile", "-NonInteractive", "-Command", script],
        env={
            **{key: value for key, value in os.environ.items() if key.upper() != "PSMODULEPATH"},
            "LYCHD_LOGIN_IDENTIFIER": registration["identifier"],
            "LYCHD_LOGIN_ARGUMENTS": " ".join(_arguments(registration)),
            "LYCHD_LOGIN_INTERPRETER": sys.executable,
            "LYCHD_LOGIN_REMOVE": "1" if remove else "0",
        },
        check=True,
    )


def _mac(registration: dict[str, str], *, remove: bool) -> None:
    identifier = registration["identifier"]
    path = _plist()
    check_path(path)
    domain = f"gui/{os.getuid()}"
    service = f"{domain}/{_LABEL}"
    expected = {
        "Label": _LABEL,
        "ProgramArguments": [sys.executable, *_arguments(registration)],
        "EnvironmentVariables": {"LYCHD_LOGIN_IDENTIFIER": identifier},
        "RunAtLoad": True,
        "StandardErrorPath": str(PATH_POSTGRES_ROOT_DIR / "desktop-session.log"),
    }
    if path.exists():
        with path.open("rb") as stream:
            if plistlib.load(stream) != expected:
                msg = f"Preserved unrecognized launch agent {path}."
                raise click.ClickException(msg)
    query = subprocess.run(["/bin/launchctl", "print", service], capture_output=True, text=True, check=False)
    loaded = query.returncode == 0
    properties: set[str] = {line.strip() for line in query.stdout.splitlines()} if loaded else set()
    if loaded and (
        not path.is_file()
        or not {f"path = {path}", f"program = {sys.executable}", f"LYCHD_LOGIN_IDENTIFIER => {identifier}"}
        <= properties
    ):
        msg = "Preserved unrecognized loaded launch agent."
        raise click.ClickException(msg)
    if remove:
        if loaded and "state = running" in properties:
            msg = "Run lychd stop before removing the active login service."
            raise click.ClickException(msg)
        if loaded:
            subprocess.run(["/bin/launchctl", "bootout", service], check=True)
        path.unlink(missing_ok=True)
    elif not loaded:
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            publish_file(path, plistlib.dumps(expected))
        subprocess.run(["/bin/launchctl", "bootstrap", domain, path], check=True)


def enable() -> None:
    """Register an unelevated service, verifying any preexisting task before use."""
    values = read_registration()
    if not values:
        _create_registration()
        values = read_registration()
    (_windows if sys.platform == "win32" else _mac)(values, remove=False)


def disable() -> None:
    """Remove only the registered task whose account, executable and installation match."""
    values = read_registration()
    if values:
        (_windows if sys.platform == "win32" else _mac)(values, remove=True)
        _PROFILE.unlink()
