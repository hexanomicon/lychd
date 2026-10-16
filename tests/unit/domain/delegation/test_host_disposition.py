"""Exact mechanical host intent codecs; no owner or physical admission fixture."""

from __future__ import annotations

import json
import pickle
from dataclasses import replace
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pytest

import lychd.domain.delegation.host_disposition as module
from lychd.domain.artifacts import ArtifactRef
from lychd.domain.delegation.host_disposition import (
    MAX_HOST_PREPARATION_BYTES,
    DelegatedHostDispositionSnapshot,
    DelegatedHostIntakeClosure,
    DelegatedHostPolicyIdentity,
    DelegatedHostPreparation,
    FreshHostPreparation,
    build_host_preparation,
    decode_host_preparation,
)
from lychd.domain.delegation.models import DelegatedAgentJobRef
from tests.support.delegated_cli import cli_request

if TYPE_CHECKING:
    from lychd.domain.delegation.cli_protocol import CliLaunchSpec
    from lychd.domain.delegation.models import DelegatedCliRequestV2


def preparation() -> DelegatedHostPreparation:
    """Build actual compiler input without any affirmative authority observation."""
    request = cli_request()
    job = DelegatedAgentJobRef(
        job_id="mechanical-job",
        request_id=request.request_id,
        run_id=request.run_id,
        runtime=request.runtime,
        profile=request.profile,
    )
    return build_host_preparation(
        job,
        request,
        policy=DelegatedHostPolicyIdentity(policy_id="unqualified-policy", revision="1", digest="sha256:" + "a" * 64),
        executor_id="unqualified-executor",
        executor_generation=0,
    )


def test_exact_canonical_round_trip_and_private_repr() -> None:
    retained = preparation()
    assert decode_host_preparation(retained.canonical_bytes()) == retained
    assert decode_host_preparation(retained.canonical_bytes()).digest == retained.digest
    assert retained.request.prompt not in repr(retained)
    assert retained.policy.digest not in repr(retained.policy)
    assert retained.request.prompt not in repr(FreshHostPreparation(retained))
    with pytest.raises(TypeError, match="cannot be serialized"):
        pickle.dumps(FreshHostPreparation(retained))


@pytest.mark.parametrize("field", ["request_digest", "intent_digest", "launch_digest", "preparation_schema"])
def test_retained_digest_and_schema_substitution_refuses(field: str) -> None:
    document = preparation().model_dump(mode="json")
    document[field] = "unknown@99" if field == "preparation_schema" else "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="validation error"):
        decode_host_preparation(json.dumps(document, separators=(",", ":"), sort_keys=True).encode())


@pytest.mark.parametrize("change", ["extra", "generation_bool", "negative_generation", "latest", "job", "request"])
def test_copied_model_bypasses_are_revalidated(change: str) -> None:
    retained = preparation()
    if change == "extra":
        altered = retained.model_copy(update={"owner_authorized": True})
    elif change == "generation_bool":
        altered = retained.model_copy(update={"executor_generation": True})
    elif change == "negative_generation":
        altered = retained.model_copy(update={"executor_generation": -1})
    elif change == "latest":
        altered = retained.model_copy(update={"policy": retained.policy.model_copy(update={"revision": "LATEST"})})
    elif change == "job":
        altered = retained.model_copy(update={"job": retained.job.model_copy(update={"extra": True})})
    else:
        altered = retained.model_copy(update={"request": retained.request.model_copy(update={"extra": True})})
    with pytest.raises(ValueError, match="validation error"):
        altered.canonical_bytes()


def test_noncanonical_and_oversized_preparation_refuse() -> None:
    retained = preparation()
    with pytest.raises(ValueError, match="not canonical"):
        decode_host_preparation(json.dumps(retained.model_dump(mode="json"), indent=2).encode())
    with pytest.raises(ValueError, match="byte ceiling"):
        decode_host_preparation(b" " * (MAX_HOST_PREPARATION_BYTES + 1))
    request = retained.request.model_copy(
        update={
            "input_artifacts": (
                ArtifactRef(
                    artifact_id="a" * MAX_HOST_PREPARATION_BYTES,
                    digest="sha256:" + "a" * 64,
                    media_type="text/plain",
                    size=1,
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="byte ceiling"):
        build_host_preparation(
            retained.job,
            request,
            policy=retained.policy,
            executor_id=retained.executor_id,
            executor_generation=retained.executor_generation,
        )


def test_current_compiler_must_reconstruct_retained_launch(monkeypatch: pytest.MonkeyPatch) -> None:
    retained = preparation().canonical_bytes()
    original = module.compile_cli_request

    def changed(request: DelegatedCliRequestV2, job: DelegatedAgentJobRef) -> CliLaunchSpec:
        spec = original(request, job)
        return replace(spec, argv=(*spec.argv, "--substituted"))

    monkeypatch.setattr(module, "compile_cli_request", changed)
    with pytest.raises(ValueError, match="compiler inputs"):
        decode_host_preparation(retained)


def test_public_snapshot_and_closure_revalidate_nested_models_and_aware_time() -> None:
    retained = preparation()
    now = datetime.now(UTC)
    snapshot = DelegatedHostDispositionSnapshot(retained.job, retained, now, None, None, None)
    assert snapshot.preparation == retained
    assert snapshot.preparation is not retained
    closure = DelegatedHostIntakeClosure(retained.job, now)
    assert closure.job == retained.job
    assert closure.job is not retained.job
    forged_job = retained.job.model_copy(update={"extra": True})
    with pytest.raises(ValueError, match="validation error"):
        replace(snapshot, job=forged_job)
    with pytest.raises(ValueError, match="validation error"):
        replace(closure, job=forged_job)
    with pytest.raises(ValueError, match="validation error"):
        replace(snapshot, preparation=retained.model_copy(update={"owner_authorized": True}))
    with pytest.raises(ValueError, match="aware datetimes"):
        replace(snapshot, prepared_at=now.replace(tzinfo=None))
    with pytest.raises(ValueError, match="aware datetimes"):
        replace(closure, closed_at=now.replace(tzinfo=None))
    with pytest.raises(ValueError, match="incomplete"):
        replace(snapshot, prepared_at=None)
