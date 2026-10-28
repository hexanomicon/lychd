from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from scripts import reach_operator as operator


@pytest.mark.parametrize("enabled", [False, True])
def test_optional_profile_is_frozen_privately_and_mounted_only_into_edge(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, enabled: bool
) -> None:
    policy = tmp_path / "policy.toml"
    token, images, state, corpus = (tmp_path / name for name in ("token", "images.json", "state", "corpus"))
    operator.write_private(
        policy,
        b"""schema_version = 1
application_id = "101"
bot_user_id = "102"
guild_id = "103"
allowed_channel_ids = ["104"]
[[rules]]
name = "operator"
user_ids = ["105"]
actions = ["answer_docs"]
""",
    )
    operator.write_private(token, b"synthetic.token.for_test_only")
    image = "sha256:" + "a" * 64
    operator.write_private(images, operator.json_bytes({"schema_version": 1, "core": image, "edge": image}))
    corpus.mkdir()
    (corpus / "manifest.json").write_text("{}")
    profile = tmp_path / "onboarding.json"
    raw = b'{"guild_id":"103","channel_id":"104","panel_message_id":"107","magus_role_id":"108","bot_role_id":"109"}'
    operator.write_private(profile, raw)
    observed: list[list[str]] = []

    async def supervise(_engine: str, commands: tuple[list[str], list[str]], _ids: tuple[Path, Path]) -> int:
        observed.extend(commands)
        core, edge = commands
        assert not any("onboarding" in item for item in core)
        if enabled:
            mounts = [item for item in edge if ":/run/reach/onboarding.json:ro,Z" in item]
            assert len(mounts) == 1
            frozen = Path(mounts[0].split(":", 1)[0])
            assert frozen != profile
            assert await asyncio.to_thread(frozen.read_bytes) == raw
            metadata = await asyncio.to_thread(frozen.stat)
            assert metadata.st_mode & 0o777 == 0o600
            await asyncio.to_thread(profile.write_bytes, b"{}")
            assert await asyncio.to_thread(frozen.read_bytes) == raw
            assert edge[edge.index("--onboarding-profile") + 1] == "/run/reach/onboarding.json"
        else:
            assert not any("onboarding" in item for item in edge)
        return 0

    monkeypatch.setattr(operator, "supervise", supervise)
    argv = [
        "run",
        "--policy",
        str(policy),
        "--token-file",
        str(token),
        "--images",
        str(images),
        "--state-dir",
        str(state),
        "--corpus-dir",
        str(corpus),
        "--engine",
        "docker",
    ]
    if enabled:
        argv += ["--onboarding-profile", str(profile)]
    assert operator.run_containers(operator.parser().parse_args(argv)) == 0
    assert len(observed) == 2


def test_host_rejects_duplicate_onboarding_keys() -> None:
    # The strict parser used for this explicit profile rejects ambiguous JSON before schema admission at the edge.
    with pytest.raises(ValueError, match="operator_duplicate_key"):
        operator.strict_object(b'{"guild_id":"103","guild_id":"999"}')
