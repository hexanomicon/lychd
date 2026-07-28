"""Golden-manifest parity test for the container/Quadlet transmutation layer.

This is the crown-jewel parity net for the self-generating container structure
(Magus's #1 worry). It pins the FOUR load-bearing properties of the transmuted
pod (brief §8) as a byte-stable golden serialization of ``transmute_all(...)``,
for BOTH scenarios: Phoenix-active and Phoenix-absent.

Machine stability: every settings-/host-derived value the manifests embed is
normalised through the SAME ``get_settings()`` / constant reads at load time
(never frozen as a literal), so the committed golden is identical on any host.
Regenerate the goldens with ``LYCHD_REGEN_GOLDEN=1 pytest ...`` after an
INTENTIONAL manifest change (a golden diff is then a reviewed, deliberate act).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import pytest

from lychd.config.settings.root import get_settings
from lychd.domain.animation.schemas import (
    ConcurrencyIntent,
    GenericSoulstoneConfig,
    OpenAIPortalConfig,
)
from lychd.domain.animation.services.adapters.registry import RuntimeAdapterRegistry
from lychd.domain.animation.transmute import Transmuter
from lychd.system import constants
from lychd.system.schemas import QuadletBase, QuadletContainer, QuadletPod, QuadletTarget
from lychd.system.unit_names import animator_service_unit, animator_target_unit, coven_target_unit

if TYPE_CHECKING:
    from collections.abc import Sequence

    from lychd.domain.animation.schemas import PortalConfig, SoulstoneConfig

from lychd.extensions.builtin.observability.phoenix.config import (
    CONTAINER_PHOENIX_OTLP_PORT,
    CONTAINER_PHOENIX_UI_PORT,
    PhoenixSettings,
)

GOLDEN_DIR = Path(__file__).parents[3] / "fixtures" / "golden" / "quadlets"
_REGEN = os.getenv("LYCHD_REGEN_GOLDEN") == "1"


# --------------------------------------------------------------------------- #
# Deterministic fixture set (no random factory fields — a golden must be exact) #
# --------------------------------------------------------------------------- #
def _soulstones() -> list[SoulstoneConfig]:
    """A deterministic stone set covering target and boot properties.

    - ``alpha`` + ``beta``: a >= 2-member coven ("logic") -> a real target.
    - ``gamma``: a solitary stone with no target membership.
    - ``resident``: a persistent resident -> WantedBy=default.target.
    """
    return [
        GenericSoulstoneConfig(
            name="alpha",
            image="registry.example/alpha:1",
            groups=["logic"],
            concurrency=ConcurrencyIntent(conflict_domains=["gpu"]),
            env_vars={"CTX": "4096"},
        ),
        GenericSoulstoneConfig(
            name="beta",
            image="registry.example/beta:1",
            groups=["logic"],
            concurrency=ConcurrencyIntent(conflict_domains=[]),
        ),
        GenericSoulstoneConfig(
            name="gamma",
            image="registry.example/gamma:1",
            groups=[],
            concurrency=ConcurrencyIntent(conflict_domains=["gpu"]),
            secret_env_files={"HF_TOKEN_FILE": "gamma_hf_token"},
        ),
        GenericSoulstoneConfig(
            name="resident",
            image="registry.example/resident:1",
            groups=[],
            concurrency=ConcurrencyIntent(dedicated=False, persistent_resident=True),
        ),
    ]


def _portals() -> list[PortalConfig]:
    """One portal with an API-key secret (pins the vessel portal-secret merge)."""
    return [
        OpenAIPortalConfig(
            name="openai-main",
            api_key_secret_name="openai_api_key",  # noqa: S106 - Podman secret name, not a secret value
        )
    ]


# --------------------------------------------------------------------------- #
# Normalisation: replace host-/settings-derived substrings with stable tokens  #
# --------------------------------------------------------------------------- #
def _replacements() -> list[tuple[str, str]]:
    settings = get_settings()
    pairs = [
        (str(constants.PATH_POSTGRESS_DATA_DIR), "${PATH_POSTGRESS_DATA_DIR}"),
        (str(constants.PATH_POSTGRES_ROOT_DIR), "${PATH_POSTGRES_ROOT_DIR}"),
        (str(constants.PATH_CORE_DIR), "${PATH_CORE_DIR}"),
        (str(constants.PATH_EXTENSIONS_DIR), "${PATH_EXTENSIONS_DIR}"),
        (str(constants.PATH_CODEX_ROOT), "${PATH_CODEX_ROOT}"),
        (str(constants.PATH_CRYPT_ROOT), "${PATH_CRYPT_ROOT}"),
        (str(Path.home()), "${HOME}"),
        (settings.server.web.image, "${APP_IMAGE}"),
        (settings.server.database.image, "${DB_IMAGE}"),
        (settings.server.web.secret_key_secret, "${APP_SECRET}"),
        (settings.server.database.password_secret, "${DB_SECRET}"),
    ]
    # Longest source first so nested paths (CORE/EXTENSIONS under CRYPT) win.
    return sorted(pairs, key=lambda pair: len(pair[0]), reverse=True)


def _normalize(value: Any) -> Any:
    """Recursively replace machine-/settings-derived substrings with tokens."""
    if isinstance(value, str):
        for actual, token in _replacements():
            if actual:
                value = value.replace(actual, token)
        return value
    if isinstance(value, list):
        items = cast("list[Any]", value)
        return [_normalize(item) for item in items]
    if isinstance(value, dict):
        mapping = cast("dict[str, Any]", value)
        return {key: _normalize(item) for key, item in mapping.items()}
    return value


def _unit_identity(manifest: QuadletBase) -> str:
    if isinstance(manifest, QuadletContainer):
        return manifest.container_name
    if isinstance(manifest, QuadletPod):
        return manifest.pod_name
    if isinstance(manifest, QuadletTarget):
        return manifest.unit_name
    msg = f"Unknown manifest kind: {type(manifest)!r}"
    raise TypeError(msg)


def _serialize(manifests: Sequence[QuadletBase]) -> list[dict[str, Any]]:
    """Deterministic, machine-stable serialization of a manifest sequence."""
    return [
        {
            "type": type(manifest).__name__,
            "id": _unit_identity(manifest),
            "dump": _normalize(manifest.model_dump(mode="json")),
        }
        for manifest in manifests
    ]


def _transmute(*, phoenix_active: bool) -> list[QuadletBase]:
    """Drive the Transmuter through the QuadletContributor seam for one scenario."""
    from lychd.config.runes.registry import RuneRegistry
    from lychd.extensions.builtin.observability.phoenix.config import PhoenixSettings
    from lychd.extensions.builtin.observability.phoenix.contributor import PhoenixQuadletContributor

    transmuter = Transmuter(
        settings=get_settings(),
        runtime_planner=RuntimeAdapterRegistry(),
        contributors=[PhoenixQuadletContributor()],
    )
    runes = RuneRegistry([PhoenixSettings()] if phoenix_active else [])
    return transmuter.transmute_all(_soulstones(), portals=_portals(), runes=runes)


def _golden_path(scenario: str) -> Path:
    return GOLDEN_DIR / f"{scenario}.json"


def _check_golden(scenario: str, *, phoenix_active: bool) -> list[dict[str, Any]]:
    actual = _serialize(_transmute(phoenix_active=phoenix_active))
    path = _golden_path(scenario)
    if _REGEN:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(actual, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    assert path.exists(), f"Missing golden {path}; regenerate with LYCHD_REGEN_GOLDEN=1."
    expected = json.loads(path.read_text(encoding="utf-8"))
    assert actual == expected, (
        f"Golden-manifest parity broke for scenario '{scenario}'. "
        "If intentional, regenerate with LYCHD_REGEN_GOLDEN=1 and review the diff."
    )
    return actual


# --------------------------------------------------------------------------- #
# The two golden scenarios (the headline exit-gate item)                       #
# --------------------------------------------------------------------------- #
def test_golden_manifest_phoenix_active() -> None:
    """Full byte-stable parity for the Phoenix-active pod."""
    _check_golden("phoenix_active", phoenix_active=True)


def test_golden_manifest_phoenix_absent() -> None:
    """Full byte-stable parity for the Phoenix-absent pod."""
    _check_golden("phoenix_absent", phoenix_active=False)


# --------------------------------------------------------------------------- #
# §8 property pins (human-readable; asserted against get_settings()/constants)  #
# --------------------------------------------------------------------------- #
def _by_id(manifests: Sequence[QuadletBase]) -> dict[str, QuadletBase]:
    return {_unit_identity(m): m for m in manifests}


def test_property1_pod_network_truth() -> None:
    """§8.1 — the pod publishes core ports, then phoenix ports (active) in order."""
    settings = get_settings()
    core = [
        f"127.0.0.1:{settings.server.port}:{constants.CONTAINER_LYCHD_PORT}",
        f"127.0.0.1:{settings.server.database.port}:{constants.CONTAINER_POSTGRES_PORT}",
    ]

    active = _transmute(phoenix_active=True)
    absent = _transmute(phoenix_active=False)
    active_pod = next(m for m in active if isinstance(m, QuadletPod))
    absent_pod = next(m for m in absent if isinstance(m, QuadletPod))

    assert absent_pod.publish_ports == core
    assert absent_pod.user_ns == "keep-id"
    assert absent_pod.shm_size is None
    phoenix = PhoenixSettings()
    assert active_pod.publish_ports == [
        *core,
        f"127.0.0.1:{phoenix.ui_port}:{CONTAINER_PHOENIX_UI_PORT}",
        f"127.0.0.1:{phoenix.otlp_port}:{CONTAINER_PHOENIX_OTLP_PORT}",
    ]


def test_property2_manifest_sequence() -> None:
    """§8 — sequence: pod -> core -> migration -> contributions -> targets -> stones."""
    active = _transmute(phoenix_active=True)
    absent = _transmute(phoenix_active=False)

    active_seq = [(type(m).__name__, _unit_identity(m)) for m in active]
    assert active_seq == [
        ("QuadletPod", "lychd"),
        ("QuadletContainer", "lychd-vessel"),
        ("QuadletContainer", "lychd-phylactery"),
        ("QuadletContainer", "lychd-migrate"),
        ("QuadletContainer", "lychd-phoenix"),
        ("QuadletTarget", animator_target_unit("alpha")),
        ("QuadletTarget", animator_target_unit("beta")),
        ("QuadletTarget", animator_target_unit("gamma")),
        ("QuadletTarget", animator_target_unit("resident")),
        ("QuadletTarget", coven_target_unit("logic")),
        ("QuadletContainer", "lychd-alpha"),
        ("QuadletContainer", "lychd-beta"),
        ("QuadletContainer", "lychd-gamma"),
        ("QuadletContainer", "lychd-resident"),
    ]

    absent_seq = [(type(m).__name__, _unit_identity(m)) for m in absent]
    assert "lychd-phoenix" not in [ident for _, ident in absent_seq]
    assert absent_seq == [
        ("QuadletPod", "lychd"),
        ("QuadletContainer", "lychd-vessel"),
        ("QuadletContainer", "lychd-phylactery"),
        ("QuadletContainer", "lychd-migrate"),
        ("QuadletTarget", animator_target_unit("alpha")),
        ("QuadletTarget", animator_target_unit("beta")),
        ("QuadletTarget", animator_target_unit("gamma")),
        ("QuadletTarget", animator_target_unit("resident")),
        ("QuadletTarget", coven_target_unit("logic")),
        ("QuadletContainer", "lychd-alpha"),
        ("QuadletContainer", "lychd-beta"),
        ("QuadletContainer", "lychd-gamma"),
        ("QuadletContainer", "lychd-resident"),
    ]


def test_property3_phoenix_eye_and_core_lattice() -> None:
    """§8.2/§8.3 — Phoenix Eye verbatim + the unit dependency lattice."""
    settings = get_settings()
    active = _by_id(_transmute(phoenix_active=True))

    phoenix = active["lychd-phoenix"]
    assert isinstance(phoenix, QuadletContainer)
    assert phoenix.pod == "lychd.pod"
    db_url = f"postgresql://{settings.server.database.user}@localhost:{constants.CONTAINER_POSTGRES_PORT}/phoenix"
    assert phoenix.env_vars == {
        "PHOENIX_PORT": str(CONTAINER_PHOENIX_UI_PORT),
        "PHOENIX_SQL_DATABASE_URL": db_url,
    }
    assert phoenix.wants == ["lychd-phylactery.service"]
    assert phoenix.after == ["lychd-phylactery.service"]

    vessel = active["lychd-vessel"]
    phylactery = active["lychd-phylactery"]
    migrator = active["lychd-migrate"]
    assert isinstance(vessel, QuadletContainer)
    assert isinstance(phylactery, QuadletContainer)
    assert isinstance(migrator, QuadletContainer)
    # Vessel env + secrets (incl. the portal secret).
    assert vessel.env_vars["LYCHD_APP_SECRET_KEY_FILE"] == f"/run/secrets/{settings.server.web.secret_key_secret}"
    assert vessel.env_vars["SERVER__DATABASE__HOST"] == "localhost"
    assert vessel.env_vars["SERVER__DATABASE__PORT"] == str(constants.CONTAINER_POSTGRES_PORT)
    assert vessel.env_vars["LYCHD_DB_PASSWORD_FILE"] == f"/run/secrets/{settings.server.database.password_secret}"
    assert "openai_api_key" in vessel.secrets
    assert settings.server.web.secret_key_secret in vessel.secrets
    assert settings.server.database.password_secret in vessel.secrets
    assert vessel.wants == ["lychd-migrate.service", "lychd-reactor.path"]
    assert vessel.requires == ["lychd-migrate.service", "lychd-reactor.path"]
    assert vessel.after == ["lychd-migrate.service", "lychd-reactor.path"]
    assert vessel.user == "%U"
    assert vessel.user_ns is None
    assert vessel.pod_service == "lychd-pod.service"
    # Phylactery hangs off the generated pod service and keeps its image user.
    assert phylactery.user is None
    assert phylactery.wants == ["lychd-pod.service"]
    assert phylactery.after == ["lychd-pod.service"]
    assert phylactery.secrets == [settings.server.database.password_secret]
    assert phylactery.env_vars["POSTGRES_PASSWORD_FILE"] == f"/run/secrets/{settings.server.database.password_secret}"
    assert phylactery.volumes[0].host_path == constants.PATH_POSTGRESS_DATA_DIR
    assert phylactery.volumes[0].options == ["U", "Z"]
    assert phylactery.volumes[1].host_path == constants.PATH_POSTGRES_ROOT_DIR / "init_db.sh"
    # Migration is a bounded one-shot dependency and shares the Vessel's path identity.
    assert migrator.service_type == "oneshot"
    assert migrator.requires == ["lychd-phylactery.service"]
    assert migrator.exec == "lychd database --wait-seconds 60 upgrade head --no-prompt"
    assert migrator.wanted_by == []


def test_property3_law_of_exclusivity_and_boot() -> None:
    """§8.3 — target arbitration, compatible aggregation, and deterministic boot."""
    active = _by_id(_transmute(phoenix_active=True))

    alpha = active["lychd-alpha"]
    gamma = active["lychd-gamma"]
    resident = active["lychd-resident"]
    alpha_target = active[animator_target_unit("alpha")]
    gamma_target = active[animator_target_unit("gamma")]
    coven = active[coven_target_unit("logic")]
    assert isinstance(alpha, QuadletContainer)
    assert isinstance(gamma, QuadletContainer)
    assert isinstance(resident, QuadletContainer)
    assert isinstance(alpha_target, QuadletTarget)
    assert isinstance(gamma_target, QuadletTarget)
    assert isinstance(coven, QuadletTarget)
    assert alpha.user == "%U"
    assert gamma.user == "%U"
    assert resident.user == "%U"
    assert alpha.wants == ["lychd-pod.service"]

    # Services cannot start without their lifecycle target. Only the
    # lease-aware Orchestrator authorizes a target switch.
    assert alpha.binds_to == [animator_target_unit("alpha")]
    assert alpha.after == ["lychd-pod.service", animator_target_unit("alpha")]
    assert alpha.conflicts == []
    assert alpha_target.requires == [animator_service_unit("alpha")]
    assert alpha_target.before == [animator_service_unit("alpha")]
    assert alpha_target.conflicts == []
    assert coven_target_unit("logic") in alpha_target.part_of

    assert gamma.conflicts == []
    assert gamma.binds_to == [animator_target_unit("gamma")]
    assert gamma_target.conflicts == [animator_target_unit("alpha")]
    assert gamma_target.after == [animator_target_unit("alpha")]

    assert coven.wants == [animator_target_unit("alpha"), animator_target_unit("beta")]
    assert coven.after == coven.wants
    assert coven.conflicts == []

    # Boot-survivor determinism (F4): only the persistent resident is auto-wanted.
    assert resident.wanted_by == ["default.target"]
    assert alpha.wanted_by == []
    assert gamma.wanted_by == []


def test_property4_coven_targets_only_for_real_covens() -> None:
    """§8 — only groups with >= 2 members forge a target."""
    active = _transmute(phoenix_active=True)
    targets = {m.name for m in active if isinstance(m, QuadletTarget) and m.kind == "coven"}
    assert targets == {"logic"}


@pytest.mark.parametrize("scenario", ["phoenix_active", "phoenix_absent"])
def test_golden_files_are_committed(scenario: str) -> None:
    """Guard: the goldens exist as committed fixtures (not regenerated silently)."""
    assert _golden_path(scenario).exists()
