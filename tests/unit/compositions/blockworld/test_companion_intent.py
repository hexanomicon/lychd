"""Closed interpretation profile and original instruction custody contracts."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import ValidationError

from lychd.compositions.blockworld.companion import strict_json
from lychd.compositions.blockworld.companion_intent import (
    CompanionInstruction,
    CompanionIntentProfile,
    load_intent_profile,
    validate_raw_instruction,
)
from lychd.domain.artifacts import ArtifactRef

_URL = "http://127.0.0.1:28761/v1"
_MODEL = "synthetic-intent"
_REQUEST = "11111111-1111-4111-8111-111111111111"
_TARGET = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"


def profile(**changes: Any) -> CompanionIntentProfile:
    return CompanionIntentProfile.model_validate({"base_url": _URL, "model_id": _MODEL, **changes})


def instruction(**changes: Any) -> CompanionInstruction:
    return CompanionInstruction.model_validate(
        {
            "request_id": _REQUEST,
            "original_text": "please stay with me",
            "generation": 3,
            "target_id": _TARGET,
            "profile_digest": profile().digest,
            "expires_at_ms": 123456789,
            **changes,
        }
    )


@pytest.mark.parametrize("url", [_URL, "http://[::1]:28761/v1"])
def test_profile_uses_one_exact_literal_local_route(url: str) -> None:
    declared = profile(base_url=url)
    assert declared.base_url == url
    assert declared.model_id == _MODEL
    assert declared.capability_key == f"companion-intent:chat:{_MODEL}"


@pytest.mark.parametrize(
    "url",
    [
        "https://127.0.0.1:28761/v1",
        "http://localhost:28761/v1",
        "http://runtime.test:28761/v1",
        "http://127.0.0.2:28761/v1",
        "http://0.0.0.0:28761/v1",
        "http://127.0.0.1/v1",
        "http://127.0.0.1:0/v1",
        "http://127.0.0.1:65536/v1",
        "http://127.0.0.1:028761/v1",
        "http://127.0.0.1:port/v1",
        "http://user@127.0.0.1:28761/v1",
        "http://user:secret@127.0.0.1:28761/v1",
        "http://[::1]/v1",
        "http://[::ffff:127.0.0.1]:28761/v1",
        f"{_URL}?token=secret",
        f"{_URL}#secret",
        f"{_URL}?",
        f"{_URL}#",
        f"{_URL}/",
        "http://127.0.0.1:28761/other",
        "http://127.0.0.1:28761/v1/../v1",
        f" {_URL}",
        f"{_URL}\n",
    ],
)
def test_profile_refuses_credentials_dns_aliases_paths_and_implicit_ports(url: str) -> None:
    with pytest.raises(ValidationError):
        profile(base_url=url)


@pytest.mark.parametrize("model_id", ["", " ", " other", "other ", "other\n", "x" * 257])
def test_profile_refuses_ambiguous_or_oversized_identity(model_id: str) -> None:
    with pytest.raises(ValidationError):
        profile(model_id=model_id)


@pytest.mark.parametrize(
    "changes",
    [
        {"context_tokens": 1023},
        {"context_tokens": 8193},
        {"context_tokens": "4096"},
        {"context_tokens": 4096.0},
        {"context_tokens": True},
        {"max_tokens": 0},
        {"max_tokens": 513},
        {"max_tokens": "512"},
        {"max_tokens": True},
        {"inference_timeout_s": 0.09},
        {"inference_timeout_s": 15.1},
        {"inference_timeout_s": "1.0"},
        {"inference_timeout_s": True},
        {"inference_timeout_s": float("nan")},
        {"inference_timeout_s": float("inf")},
        {"inference_timeout_s": float("-inf")},
        {"max_requests": 0},
        {"max_requests": 33},
        {"max_requests": "16"},
        {"max_requests": True},
        {"version": 2},
        {"version": True},
        {"version": 1.0},
        {"version": "1"},
        {"fallback": "remote"},
    ],
)
def test_profile_strict_numeric_ceilings_and_closed_keys(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        profile(**changes)


def test_profile_accepts_budget_boundaries_and_keeps_input_capacity() -> None:
    low = profile(context_tokens=1024, max_tokens=1, inference_timeout_s=0.1, max_requests=1)
    high = profile(context_tokens=8192, max_tokens=512, inference_timeout_s=15.0, max_requests=32)
    assert low.max_tokens < low.context_tokens
    assert high.max_tokens < high.context_tokens


def test_profile_digest_is_stable_for_json_key_order_and_changes_with_binding() -> None:
    declared = profile()
    reversed_keys = dict(reversed(list(declared.model_dump(mode="json").items())))
    loaded = load_intent_profile(json.dumps(reversed_keys))
    assert loaded == declared
    assert loaded.digest == declared.digest
    assert declared.digest.startswith("sha256:")
    assert len(declared.digest) == 71
    for changes in ({"model_id": "another"}, {"max_tokens": 511}, {"base_url": "http://[::1]:28761/v1"}):
        assert profile(**changes).digest != declared.digest
    with pytest.raises(ValidationError, match="frozen"):
        declared.model_id = "changed"


@pytest.mark.parametrize(
    "document",
    [
        '{"base_url":"http://127.0.0.1:28761/v1","model_id":"one","model_id":"two"}',
        '{"base_url":"http://127.0.0.1:28761/v1","model_id":"one","max_tokens":NaN}',
        '{"base_url":"http://127.0.0.1:28761/v1","model_id":"one","inference_timeout_s":Infinity}',
        '{"base_url":"http://127.0.0.1:28761/v1","model_id":"one","inference_timeout_s":-Infinity}',
        '{"base_url":"http://127.0.0.1:28761/v1","model_id":"one","inference_timeout_s":1e1000}',
        "[]",
        "{} trailing",
    ],
)
def test_profile_loader_refuses_duplicate_nonfinite_and_malformed_json(document: str) -> None:
    with pytest.raises(ValueError, match=r"Duplicate|Non-finite|dictionary|Extra data"):
        load_intent_profile(document)


def test_profile_loader_accepts_utf8_bytes_and_refuses_invalid_or_oversized_document() -> None:
    declared = profile()
    assert load_intent_profile(declared.model_dump_json().encode()) == declared
    for document in (b"\xff", b" " * 100000):
        with pytest.raises(ValueError, match=r"utf-8|byte limit"):
            load_intent_profile(document)


def test_instruction_preserves_original_transcript_and_immutable_binding() -> None:
    original = " \tprosím zostaň pri mne\r\n"
    captured = instruction(original_text=original, source="transcript", language="sk")
    assert captured.original_text == original
    assert captured.instruction == "prosím zostaň pri mne"
    assert captured.generation == 3
    assert captured.target_id == _TARGET
    assert captured.expires_at_ms == 123456789
    for field, value in (("original_text", "different"), ("generation", 4), ("expires_at_ms", 999999999)):
        with pytest.raises(ValidationError, match="frozen"):
            setattr(captured, field, value)


def test_instruction_source_artifacts_survive_strict_json_roundtrip() -> None:
    artifact = ArtifactRef(
        artifact_id="synthetic-transcript",
        digest="sha256:" + "a" * 64,
        media_type="text/plain",
        size=41,
        classification="private",
    )
    captured = instruction(source="transcript", source_artifacts=(artifact,))
    restored = CompanionInstruction.model_validate(strict_json(captured.model_dump_json()))
    assert restored == captured
    assert restored.source_artifacts == (artifact,)
    assert isinstance(restored.source_artifacts, tuple)
    with pytest.raises(ValidationError, match="frozen"):
        restored.source_artifacts[0].digest = "sha256:" + "b" * 64
    with pytest.raises(ValidationError):
        instruction(source_artifacts=(artifact,) * 5)


@pytest.mark.parametrize(
    "changes",
    [
        {"request_id": "not-a-uuid"},
        {"request_id": _REQUEST.replace("-", "")},
        {"target_id": _TARGET.upper()},
        {"target_id": "player-name"},
        {"generation": -1},
        {"generation": True},
        {"generation": "3"},
        {"expires_at_ms": 0},
        {"expires_at_ms": "123"},
        {"expires_at_ms": True},
        {"profile_digest": "sha256:" + "A" * 64},
        {"profile_digest": "model-name"},
        {"source": "microphone"},
        {"language": "xx"},
        {"kind": "action"},
        {"new_target": _TARGET},
    ],
)
def test_instruction_refuses_mutable_identity_and_coerced_custody(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        instruction(**changes)


@pytest.mark.parametrize(
    "text",
    [
        "state extra",
        "STATE extra",
        "stav navyše",
        "idle extra",
        "čakaj extra",
        "čekej extra",
        "look sideways",
        "pozri tam",
        "podívej sem",
        "goto near me",
        "choď sem",
        "jdi tam",
        "say private text",
        "povedz niečo",
        "řekni něco",
        f"follow {_TARGET}",
        f"follow player {_TARGET}",
        "please follow aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        "follow PrivatePlayer",
        "nasleduj suseda",
        "please go to 12 64 -3",
        "please go to twelve:sixty",
        "please go /home",
        "please wait\x00here",
        "please wait\u0085here",
        "please wait\nhere",
        "please\twait",
        " ",
        "a" * 1001,
    ],
)
def test_unsafe_raw_input_and_malformed_reserved_commands_refuse_before_interpretation(text: str) -> None:
    with pytest.raises(ValueError, match="outside the bounded interpretation"):
        validate_raw_instruction(text)
    with pytest.raises(ValidationError):
        instruction(original_text=text)


@pytest.mark.parametrize("text", ["stay with me please", "zostaň pri mne prosím", "zůstaň u mě prosím", "follow me"])
def test_bounded_instruction_does_not_rewrite_eligible_text(text: str) -> None:
    assert validate_raw_instruction(text) == text
    assert instruction(original_text=text).original_text == text


@pytest.mark.parametrize(
    "text",
    [
        "look.",
        "look! around",
        "state. extra",
        "idle! then follow",
        "say!",
        "goto?",
        "follow?",
        "follow? me",
        "follow, me",
        "f!o!l!l!o!w me",
        "nasleduj! ma",
        "následuj! mě",
        "follow  me",
        "goto\u00a0near me",
        "look\u00a0around",
    ],
)
def test_decorated_or_respaced_strict_heads_are_not_repaired(text: str) -> None:
    with pytest.raises(ValueError, match="outside the bounded interpretation"):
        validate_raw_instruction(text)
