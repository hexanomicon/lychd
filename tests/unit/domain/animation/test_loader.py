from __future__ import annotations

from pathlib import Path

import pytest

from lychd.domain.animation.schemas import (
    AnimatorConfig,
    GenericSoulstoneConfig,
    GoogleGeminiPortalConfig,
    OpenAIPortalConfig,
    PortalConfig,
    SoulstoneConfig,
)
from lychd.domain.animation.services.loader import AnimatorConfigError, AnimatorLoader
from lychd.extensions.builtin.animator import (
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
    LlamaCppSoulstoneConfig,
    VllmSoulstoneConfig,
    SglangSoulstoneConfig,
    OpenAIPortalConfig,
    GoogleGeminiPortalConfig,
]


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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={"Postgres": 5432})

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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
    _, portals = loader.load_all()

    assert len(portals) == 1
    assert portals[0].api_key_secret_name == "portal_secure_api_key"  # noqa: S105 - secret name fixture


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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})
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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="duplicate soulstone name"):
        loader.load_all()


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

    loader = AnimatorLoader(runes_dir=runes_dir, rune_schemas=_SCHEMAS, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="used by both soulstone and portal"):
        loader.load_all()
