"""Preview a finite connected Reach plan without credentials, network or delivery."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import Field

from lychd.compositions.reach.connected.policy import prepare_batch
from lychd.compositions.reach.connected.providers import build_request
from lychd.compositions.reach.connected.schemas import ConnectedPolicy, CorrespondenceRequest, Record

MAX_DOCUMENT_BYTES = 262_144


class RequestDocument(Record):
    """A bounded local fixture; this is not an authenticated ingress envelope."""

    requests: tuple[CorrespondenceRequest, ...] = Field(min_length=1, max_length=32, repr=False)


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate JSON key."
            raise ValueError(msg)
        result[key] = value
    return result


def _read(path: Path) -> str:
    with path.open("rb") as source:
        document = source.read(MAX_DOCUMENT_BYTES + 1)
    if len(document) > MAX_DOCUMENT_BYTES:
        msg = "Connected preparation document exceeds its size limit."
        raise ValueError(msg)
    # Reject duplicate keys before schema validation; JSON mode admits JSON arrays as tuples.
    return json.dumps(json.loads(document.decode("utf-8"), object_pairs_hook=_unique), allow_nan=False)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path, help="Explicit nonsecret JSON preparation policy.")
    parser.add_argument("--requests", required=True, type=Path, help="Exact local requests JSON.")
    parser.add_argument(
        "--include-payload", action="store_true", help="Include private application payloads in stdout for inspection."
    )
    args = parser.parse_args(argv)
    try:
        policy = ConnectedPolicy.model_validate_json(_read(args.policy))
        document = RequestDocument.model_validate_json(_read(args.requests))
        batch = prepare_batch(policy, document.requests, now=datetime.now(UTC))
        # Build all items before emitting any output: an unsupported last target refuses the plan.
        requests = tuple(build_request(item) for item in batch.operations)
        output: dict[str, Any] = {
            "status": "prepared",
            "profile": "reach.connect.prepare@1",
            "preparation_only": True,
            "delivery": "not_attempted",
            "count": len(requests),
            "expires_at": batch.expires_at.isoformat(),
        }
        if args.include_payload:
            output["batch"] = batch.model_dump(mode="json")
            output["requests"] = [item.model_dump(mode="json") for item in requests]
    except (OSError, ValueError, TypeError):
        sys.stderr.write("Invalid or unsupported connected Reach preparation.\n")
        return 1
    sys.stdout.write(json.dumps(output, sort_keys=True, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
