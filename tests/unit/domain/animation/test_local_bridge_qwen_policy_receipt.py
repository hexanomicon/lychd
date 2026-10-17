"""Guard dated policy-observation integrity/privacy; this does not rerun inference."""

from __future__ import annotations

import json
import re
from hashlib import sha256
from pathlib import Path

_RECEIPT = Path(__file__).resolve().parents[4] / "tests/fixtures/animator/local-bridge-qwen-policy-bf1162f.json"


def test_dated_qwen_policy_observation_keeps_content_and_verdict_separate() -> None:
    record = json.loads(_RECEIPT.read_text())
    assert record["schema"] == "local-bridge-qwen-policy-observation@1"
    assert record["record_kind"] == "sanitized_public_dated_operator_observation"
    assert record["execution_revision"] == "bf1162f7df7ceaee75c0ab1c2f3180243b7edf94"
    assert record["target_revision"] == "df637032e41c34a9c86f5fe24d7be022f501914d"
    assert not record["current_checkout_qualified"]
    assert not record["atomic_transitive_closure_attested"]
    assert record["profile"]["thinking"] == "qwen3.8-non-thinking"
    assert record["profile"]["observed_sdk_body_subset"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert (record["profile"]["context_tokens"], record["profile"]["maximum_output_tokens"]) == (4096, 256)
    assert record["profile"]["deadline_seconds"] == 30
    assert record["profile"]["maximum_posts"] == 3
    assert record["execution"]["boots"] == "two-ordinary-in-process-lifespans"
    for container, text_key, digest_key in (("input", "prompt", "prompt_sha256"), ("candidate", "text", "sha256")):
        assert sha256(record[container][text_key].encode()).hexdigest() == record[container][digest_key]
    assert not record["candidate"]["modified_after_model"]
    assert record["outcome"]["run_status"] == "DONE"
    assert record["outcome"]["model_posts"] == record["outcome"]["model_successes"] == 1
    assert record["outcome"]["generated_token_delta"] == 196 <= record["profile"]["maximum_output_tokens"]
    assert record["outcome"]["second_boot_model_posts"] == 0
    assert record["outcome"]["retained_history_identical"]
    review = record["independent_review"]
    assert review["verdict"] == "partial"
    assert not review["answer_accepted_verbatim"]
    assert not review["native_verifier_implemented"]
    assert not review["constructor_context_shared"]
    assert "contains capability" in review["concrete_bypass_example"]
    example = re.search(r'e.g., "([^"]+)"', record["candidate"]["text"])
    assert example is not None
    assert "capability" in example.group(1).casefold()
    assert "native independent verification" in record["unexercised"]
    assert "autonomous development or promotion" in record["unexercised"]
    for digest in (*record["source_fingerprints_observed"].values(), *record["evidence_sha256"].values()):
        assert re.fullmatch(r"[0-9a-f]{64}", digest)


def test_dated_qwen_policy_observation_contains_no_operator_identity() -> None:
    text = _RECEIPT.read_text()
    for private_fragment in ("/home/", "/tmp/", "127.0.0.1:", "password", "Bearer ", "BEGIN PRIVATE KEY"):  # noqa: S108 - forbidden publication fragments, not file creation
        assert private_fragment not in text
