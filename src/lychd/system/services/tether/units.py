"""Fixed plain-unit projections consumed by complete-fileset Scribe binding."""

from __future__ import annotations

from pathlib import Path

from lychd.domain.tether.models import CompiledTetherPlan
from lychd.system.constants import PATH_XDG_CACHE_HOME, PATH_XDG_CONFIG_HOME, PATH_XDG_DATA_HOME
from lychd.system.schemas import systemd_environment_assignment
from lychd.system.services.tether.models import TetherError


def _word(value: str) -> str:
    if not value.startswith("/") or any(character in value for character in '\n\r\x00%"\\'):
        msg = "Tether unit projection requires a safe absolute host path"
        raise TetherError(msg)
    return '"' + value + '"'


def render_tether_units(plan: CompiledTetherPlan, *, crypt_root: Path, executable: Path) -> dict[str, str]:
    """Return two fixed plain units using an installed trusted Python executable; this function never writes or reconciles units."""
    latch = _word(str(crypt_root / plan.closure_relative_path))
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
