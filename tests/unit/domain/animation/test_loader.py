from __future__ import annotations

from pathlib import Path

import pytest

from lychd.domain.animation.services.loader import AnimatorConfigError, AnimatorLoader


@pytest.fixture
def runes_dir(tmp_path: Path) -> Path:
    root = tmp_path / "runes"
    (root / "animator" / "soulstones").mkdir(parents=True, exist_ok=True)
    (root / "animator" / "portals").mkdir(parents=True, exist_ok=True)
    return root


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{content.strip()}\n", encoding="utf-8")


def test_load_soulstone_from_top_level_payload(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "hermes.toml",
        """
        name = "hermes"
        image = "ghcr.io/ggerganov/llama.cpp:server"
        port = 8080
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})
    soulstones, portals = loader.load_all()

    assert len(soulstones) == 1
    assert len(portals) == 0
    assert soulstones[0].name == "hermes"
    assert soulstones[0].base_url == "http://localhost:8080/v1"


def test_animator_singleton_defaults_are_inherited_by_portals(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "animator.toml",
        """
        name = "animator"
        orchestration_labels = ["remote", "default"]
        """,
    )
    _write(
        runes_dir / "animator" / "portals" / "openai.toml",
        """
        name = "openai"
        provider_type = "openai"
        base_url = "https://api.openai.com/v1"
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})
    _, portals = loader.load_all()

    assert len(portals) == 1
    portal = portals[0]
    assert portal.base_url == "https://api.openai.com/v1"
    assert portal.orchestration_labels == ["remote", "default"]


def test_portal_requires_uri_after_default_merge(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "portals" / "broken.toml",
        """
        name = "broken"
        default_model_id = "gpt-like"
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="requires 'base_url'"):
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

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="Port conflicts detected"):
        loader.load_all()


def test_reserved_port_conflict(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "rogue.toml",
        """
        name = "rogue"
        image = "img"
        port = 5432
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={"Postgres": 5432})

    with pytest.raises(AnimatorConfigError, match="conflicts with Postgres"):
        loader.load_all()


def test_portal_api_key_secret_reference(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "portals" / "secure.toml",
        """
        name = "secure"
        base_url = "https://api.example.com/v1"
        default_model_id = "example-model"
        api_key_secret = "portal_secure_api_key"
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})
    _, portals = loader.load_all()

    assert len(portals) == 1
    assert portals[0].api_key_secret == "portal_secure_api_key"  # noqa: S105 - secret name fixture


def test_soulstone_secret_env_files_reference(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "secure.toml",
        """
        name = "secure-local"
        image = "vllm/vllm-openai:latest"

        [secret_env_files]
        HF_TOKEN_FILE = "hf_runtime_token"
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})
    soulstones, _ = loader.load_all()

    assert len(soulstones) == 1
    assert soulstones[0].secret_env_files["HF_TOKEN_FILE"] == "hf_runtime_token"  # noqa: S105


def test_generated_placeholder_samples_are_ignored(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "sample.toml",
        """
        name = "<required:str>"
        image = "<required:str>"
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})
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

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})
    soulstones, _ = loader.load_all()

    assert len(soulstones) == 1
    assert type(soulstones[0]).__name__ == "LlamaCppSoulstone"
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

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="exec passthrough"):
        loader.load_all()


def test_vllm_managed_mode_requires_model_source(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "invalid.toml",
        """
        name = "invalid-vllm"
        tensor_parallel_size = 2
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="requires 'model_path'"):
        loader.load_all()


def test_vllm_exec_passthrough_rejects_managed_field_mixing(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "vllm" / "invalid-exec.toml",
        """
        name = "invalid-vllm-exec"
        exec = ["vllm", "serve", "/models/qwen-awq"]
        max_model_len = 32768
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="exec passthrough"):
        loader.load_all()


def test_sglang_managed_mode_requires_model_source(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "sglang" / "invalid.toml",
        """
        name = "invalid-sglang"
        tensor_parallel_size = 2
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="requires 'model_path'"):
        loader.load_all()


def test_sglang_exec_passthrough_rejects_managed_field_mixing(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "sglang" / "invalid-exec.toml",
        """
        name = "invalid-sglang-exec"
        exec = ["python3", "-m", "sglang.launch_server", "--model-path", "/models/qwen-awq"]
        quantization = "awq"
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="exec passthrough"):
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

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="duplicate soulstone name"):
        loader.load_all()


def test_duplicate_name_across_soulstone_and_portal_is_rejected(runes_dir: Path) -> None:
    _write(
        runes_dir / "animator" / "soulstones" / "llamacpp" / "stone.toml",
        """
        name = "dupe"
        model_path = "/models/qwen.gguf"
        port = 8080
        """,
    )
    _write(
        runes_dir / "animator" / "portals" / "portal.toml",
        """
        name = "dupe"
        provider_type = "openai"
        base_url = "https://api.openai.com/v1"
        """,
    )

    loader = AnimatorLoader(runes_dir=runes_dir, reserved_ports={})

    with pytest.raises(AnimatorConfigError, match="used by both soulstone and portal"):
        loader.load_all()
