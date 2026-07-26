from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from lychd.config.runes import ConfigLoader, RuneConfig
from lychd.domain.animation.schemas import (
    AnimatorConfig,
    CapabilityFamily,
    GenericSoulstoneConfig,
    GoogleGeminiPortalConfig,
    OpenAIPortalConfig,
    PortalConfig,
    SoulstoneConfig,
)
from lychd.domain.animation.services.loader import (
    AnimatorConfigError,
)
from lychd.domain.animation.services.loader import (
    AnimatorLoader as _PureAnimatorLoader,
)
from lychd.extensions.builtin.animator import (
    ExLlamaV3SoulstoneConfig,
    LlamaCppSoulstoneConfig,
    SglangSoulstoneConfig,
    VllmSoulstoneConfig,
)

# The builtin rune schema set the loader validates against (now a required arg).
# Branch bases (AnimatorConfig/SoulstoneConfig/PortalConfig) are included so the
# loader recognises — and rejects — direct branch-path TOML, mirroring production.
_SCHEMAS = [
    AnimatorConfig,
    SoulstoneConfig,
    PortalConfig,
    GenericSoulstoneConfig,
    ExLlamaV3SoulstoneConfig,
    LlamaCppSoulstoneConfig,
    VllmSoulstoneConfig,
    SglangSoulstoneConfig,
    OpenAIPortalConfig,
    GoogleGeminiPortalConfig,
]


class _FilesystemAnimatorLoader:
    """Test composition adapter around the pure production hydrator."""

    def __init__(
        self,
        *,
        runes_dir: Path,
        rune_schemas: Sequence[type[RuneConfig]],
        reserved_ports: dict[str, int],
        core_secret_names: tuple[str, str] = (
            "lychd_app_secret_key",
            "lychd_db_password",
        ),
    ) -> None:
        self._runes_dir = runes_dir
        self._rune_schemas = list(rune_schemas)
        self._hydrator = _PureAnimatorLoader(
            reserved_ports=reserved_ports,
            core_secret_names=core_secret_names,
        )

    def load_all(self) -> tuple[list[SoulstoneConfig], list[PortalConfig]]:
        try:
            runes = ConfigLoader(self._runes_dir).load_all(self._rune_schemas)
        except ValueError as exc:
            message = f"Failed to load animation runes: {exc}"
            raise AnimatorConfigError(message) from exc
        return self._hydrator.hydrate_all(runes)


_loader = _FilesystemAnimatorLoader


@pytest.fixture
def runes_dir(tmp_path: Path) -> Path:
    root = tmp_path / "runes"
    (root / "animator" / "soulstones").mkdir(parents=True, exist_ok=True)
    (root / "animator" / "portals").mkdir(parents=True, exist_ok=True)
    return root


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content.strip()}\n", encoding="utf-8")


def test_load_concrete_soulstone_from_top_level_payload(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "generic" / "hermes.toml",
        """
        name = "hermes"
        image = "custom/local-runtime:latest"
        port = 8080
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
    soulstones, portals = loader.load_all()

    assert len(soulstones) == 1
    assert len(portals) == 0
    assert type(soulstones[0]).__name__ == "GenericSoulstoneConfig"
    assert soulstones[0].name == "hermes"
    assert str(soulstones[0].base_url) == "http://localhost:8080/v1"


def test_animator_branch_config_rejects_direct_toml(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "animator.toml",
        """
        name = "animator"
        orchestration_labels = ["remote", "default"]
        dedicated = false
        persistent_resident = true
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="AnimatorConfig"):
        loader.load_all()


def test_portal_branch_config_rejects_direct_toml(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "portals" / "broken.toml",
        """
        name = "broken"
        description = "Misplaced direct portal"
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="PortalConfig"):
        loader.load_all()


def test_port_conflict_detection(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "alpha.toml",
        """
        name = "alpha"
        model_path = "/models/alpha.gguf"
        port = 8080
        """,
    )
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "beta.toml",
        """
        name = "beta"
        model_path = "/models/beta.gguf"
        port = 8080
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="Port conflicts detected"):
        loader.load_all()


def test_reserved_port_conflict(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "rogue.toml",
        """
        name = "rogue"
        model_path = "/models/rogue.gguf"
        port = 5432
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={"Postgres": 5432})

    with pytest.raises(AnimatorConfigError, match="conflicts with Postgres"):
        loader.load_all()


def test_portal_api_key_secret_reference(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "portals" / "openai" / "secure.toml",
        """
        name = "secure"
        description = "Secure OpenAI portal"
        api_key_secret_name = "portal_secure_api_key"
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
    _, portals = loader.load_all()

    assert len(portals) == 1
    assert portals[0].api_key_secret_name == "portal_secure_api_key"  # noqa: S105 - secret name fixture


def test_portal_api_secret_cannot_alias_a_core_secret(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "portals" / "openai" / "stolen.toml",
        """
        name = "stolen"
        api_key_secret_name = "core_db"
        """,
    )
    loader = _loader(
        runes_dir=runes_dir,
        rune_schemas=_SCHEMAS,
        reserved_ports={},
        core_secret_names=("core_app", "core_db"),
    )

    with pytest.raises(AnimatorConfigError, match="cannot alias core application or database secrets"):
        loader.load_all()


def test_portals_may_deliberately_share_one_provider_secret(runes_dir: Path) -> None:
    for name in ("primary", "fallback"):
        _write(
            runes_dir / "animator" / "portals" / "openai" / f"{name}.toml",
            f"""
            name = "{name}"
            api_key_secret_name = "shared_provider_key"
            """,
        )

    _, portals = _loader(
        runes_dir=runes_dir,
        rune_schemas=_SCHEMAS,
        reserved_ports={},
        core_secret_names=("core_app", "core_db"),
    ).load_all()

    assert [portal.api_key_secret_name for portal in portals] == ["shared_provider_key"] * 2


def test_soulstones_cannot_share_one_control_plane_secret(runes_dir: Path) -> None:
    for name in ("primary", "fallback"):
        _write(
            runes_dir / "animator" / "soulstones" / "exllamav3" / f"{name}.toml",
            f"""
            name = "{name}"
            auth_secret_name = "shared_tabby_control"
            volumes = ["/data/{name}:/app/models:ro"]

            [[models]]
            id = "{name}-model"
            path = "/app/models/{name}-model"
            format = "EXL3"
            """,
        )

    with pytest.raises(AnimatorConfigError, match="cannot share control-plane secret"):
        _loader(
            runes_dir=runes_dir,
            rune_schemas=_SCHEMAS,
            reserved_ports={},
            core_secret_names=("core_app", "core_db"),
        ).load_all()


def test_soulstone_secret_env_files_reference(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "secure.toml",
        """
        name = "secure-local"
        model_path = "/models/secure.gguf"

        [secret_env_files]
        HF_TOKEN_FILE = "hf_runtime_token"
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
    soulstones, _ = loader.load_all()

    assert len(soulstones) == 1
    assert soulstones[0].secret_env_files["HF_TOKEN_FILE"] == "hf_runtime_token"  # noqa: S105


def test_generated_placeholder_samples_are_ignored(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "sample.toml",
        """
        name = "<required:str>"
        model_path = "<required:str>"
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
    soulstones, portals = loader.load_all()

    assert soulstones == []
    assert portals == []


def test_loader_hydrates_builtin_soulstone_subclass(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "hermes.toml",
        """
        name = "hermes"
        model_path = "/models/hermes.gguf"
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
    soulstones, _ = loader.load_all()

    assert len(soulstones) == 1
    assert type(soulstones[0]).__name__ == "LlamaCppSoulstoneConfig"
    assert soulstones[0].name == "hermes"


def test_llamacpp_exec_passthrough_rejects_managed_field_mixing(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "invalid.toml",
        """
        name = "invalid"
        exec = ["llama-server", "-m", "/models/qwen.gguf"]
        n_ctx = 65536
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="exec passthrough"):
        loader.load_all()


def test_vllm_rejects_reintroduced_framework_field(runes_dir: Path) -> None:
    # vLLM is exec-passthrough-only: framework flags belong in `exec`, never as
    # typed config fields. `extra="forbid"` rejects any reintroduced flag.
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "invalid.toml",
        """
        name = "invalid-vllm"
        tensor_parallel_size = 2
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="tensor_parallel_size"):
        loader.load_all()


def test_vllm_exec_passthrough_rejects_framework_field(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "invalid-exec.toml",
        """
        name = "invalid-vllm-exec"
        exec = ["vllm", "serve", "/models/qwen-awq"]
        max_model_len = 32768
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="max_model_len"):
        loader.load_all()


def test_sglang_rejects_reintroduced_framework_field(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "sglang" / "invalid.toml",
        """
        name = "invalid-sglang"
        tensor_parallel_size = 2
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="tensor_parallel_size"):
        loader.load_all()


def test_sglang_exec_passthrough_rejects_framework_field(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "sglang" / "invalid-exec.toml",
        """
        name = "invalid-sglang-exec"
        exec = ["python3", "-m", "sglang.launch_server", "--model-path", "/models/qwen-awq"]
        quantization = "awq"
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="quantization"):
        loader.load_all()


def test_duplicate_soulstone_names_are_rejected(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "a.toml",
        """
        name = "shared"
        model_path = "/models/a.gguf"
        port = 8081
        """,
    )
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "b.toml",
        """
        name = "shared"
        model_path = "/models/b.gguf"
        port = 8082
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="duplicate soulstone name"):
        loader.load_all()


def test_soulstone_models_and_generation_round_trip(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "multi.toml",
        """
        name = "multi"
        startup_mode = "router"
        models_dir = "/models"

        [generation]
        max_tokens = 1024

        [[models]]
        id = "chat-a"
        path = "/models/chat-a"
        [models.capabilities]
        modalities_in = ["text", "image"]

        [[models]]
        id = "embed-a"
        path = "/models/embed-a"
        [models.capabilities]
        families = ["embedding"]
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
    soulstones, _ = loader.load_all()

    assert len(soulstones) == 1
    stone = soulstones[0]
    assert [model.id for model in stone.models] == ["chat-a", "embed-a"]
    assert stone.generation is not None
    assert stone.generation.max_tokens == 1024
    assert stone.models[0].capabilities is not None
    assert stone.models[0].capabilities.modalities_in == ["text", "image"]
    assert stone.models[1].capabilities is not None
    assert stone.models[1].capabilities.families == [CapabilityFamily.EMBEDDING]


def test_portal_models_and_probe_round_trip(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "portals" / "openai" / "main.toml",
        """
        name = "portal-main"
        probe = true

        [[models]]
        id = "gpt-x"
        [models.capabilities]
        supports_tools = true
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
    _, portals = loader.load_all()

    assert len(portals) == 1
    portal = portals[0]
    assert portal.probe is True
    assert [model.id for model in portal.models] == ["gpt-x"]
    assert portal.models[0].capabilities is not None
    assert portal.models[0].capabilities.supports_tools is True


def test_duplicate_name_across_soulstone_and_portal_is_rejected(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "stone.toml",
        """
        name = "dupe"
        description = "Duplicate LlamaCpp soulstone"
        port = 8080
        exec = ["llama-server"]
        """,
    )
    _write(
        runes_dir / "animator" / "portals" / "openai" / "portal.toml",
        """
        name = "dupe"
        description = "Duplicate OpenAI portal"
        """,
    )

    loader = _loader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="used by both soulstone and portal"):
        loader.load_all()
