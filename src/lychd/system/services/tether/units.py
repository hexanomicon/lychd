"""Fixed plain-unit projections consumed by complete-fileset Scribe binding."""

from __future__ import annotations

from pathlib import Path

from lychd.domain.tether.models import CompiledTetherPlan
from lychd.system.constants import PATH_CODEX_ROOT, PATH_XDG_CACHE_HOME, PATH_XDG_CONFIG_HOME, PATH_XDG_DATA_HOME
from lychd.system.schemas import systemd_environment_assignment
from lychd.system.services.tether.models import TetherError


def _word(value: str) -> str:
    if not value.startswith("/") or any(character in value for character in '\n\r\x00%"\\'):
        msg = "Tether unit projection requires a safe absolute host path"
        raise TetherError(msg)
    return '"' + value + '"'


def _condition_path(path: Path) -> str:
    """Encode a fixed condition or watcher path using systemd scalar syntax."""
    value = str(path)
    if (
        not path.is_absolute()
        or ".." in path.parts
        or value != value.strip()
        or (not value.isprintable() or "\\" in value)
    ):
        msg = "Tether unit path requires a safe canonical absolute path"
        raise TetherError(msg)
    return value.replace("%", "%%")


def render_tether_units(plan: CompiledTetherPlan, *, crypt_root: Path, executable: Path) -> dict[str, str]:
    """Return two fixed plain units using an installed trusted Python executable; this function never writes or reconciles units."""
    peer = _condition_path(PATH_CODEX_ROOT / plan.intent_relative_path)
    latch = _condition_path(crypt_root / plan.closure_relative_path)
    command = _word(str(executable))
    transport = " ".join(plan.transport_units)
    environment = {
        "HOME": str(Path.home()),
        "XDG_CONFIG_HOME": str(PATH_XDG_CONFIG_HOME),
        "XDG_DATA_HOME": str(PATH_XDG_DATA_HOME),
        "XDG_CACHE_HOME": str(PATH_XDG_CACHE_HOME),
    }
    assignments = "\n".join(
        f"Environment={systemd_environment_assignment(key, value)}" for key, value in sorted(environment.items())
    )
    return {
        plan.guard_unit: f"""[Unit]
Description=LychD Tether persistent closure guard
ConditionPathExists={peer}
StartLimitIntervalSec=infinity
StartLimitBurst=3

[Path]
PathExists={latch}
Unit={plan.closure_unit}

[Install]
WantedBy=default.target
""",
        plan.closure_unit: f"""[Unit]
Description=LychD Tether monotonic closure handler
Conflicts={transport}
After={transport}
StartLimitIntervalSec=infinity
StartLimitBurst=3

[Service]
Type=oneshot
RemainAfterExit=yes
{assignments}
ExecStart={command} -m lychd.system.services.tether.composition close
TimeoutStartSec=60
TimeoutStopSec=10
""",
    }
