"""Validate an explicit Reach preparation policy without credentials or effects."""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

from lychd.compositions.reach.policy import prepare_turn
from lychd.compositions.reach.schemas import ReachEvent
from lychd.interface.discord.schemas import DiscordPolicy

MAX_DOCUMENT_BYTES = 65_536
VIEW_CHANNEL = 1 << 10
SEND_MESSAGES = 1 << 11
READ_MESSAGE_HISTORY = 1 << 16


def _read(path: Path) -> bytes:
    with path.open("rb") as source:
        document = source.read(MAX_DOCUMENT_BYTES + 1)
    if len(document) > MAX_DOCUMENT_BYTES:
        msg = "Preparation document exceeds 64 KiB."
        raise ValueError(msg)
    return document


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            msg = "Duplicate JSON key."
            raise ValueError(msg)
        result[key] = value
    return result


def load_policy(path: Path) -> DiscordPolicy:
    """Read only the named TOML policy; unknown fields and duplicate keys fail."""
    document = tomllib.loads(_read(path).decode("utf-8"))
    return DiscordPolicy.model_validate_json(json.dumps(document))


def installation_url(policy: DiscordPolicy) -> str:
    """Preview minimal guild installation scopes; no OAuth request is made."""
    permissions = VIEW_CHANNEL | SEND_MESSAGES
    if policy.context_message_limit:
        permissions |= READ_MESSAGE_HISTORY
    query = urlencode(
        {
            "client_id": policy.application_id,
            "scope": "bot applications.commands",
            "permissions": str(permissions),
            "guild_id": policy.guild_id,
            "disable_guild_select": "true",
            "integration_type": "0",
        }
    )
    return f"https://discord.com/oauth2/authorize?{query}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", required=True, type=Path, help="Explicit non-secret TOML policy.")
    parser.add_argument(
        "--event", type=Path, help="Optional normalized synthetic JSON event; timestamps must be fresh."
    )
    parser.add_argument("--install-url", action="store_true", help="Print an installation URL without opening it.")
    args = parser.parse_args(argv)
    try:
        policy = load_policy(args.policy)
        output: dict[str, Any] = {
            "status": "configuration_valid",
            "policy_digest": policy.digest,
            "preparation_only": True,
            "delivery": "not_attempted",
        }
        exit_code = 0
        if args.event is not None:
            document = json.loads(_read(args.event).decode("utf-8"), object_pairs_hook=_unique)
            event = ReachEvent.model_validate_json(json.dumps(document))
            decision = prepare_turn(policy.to_reach_policy(), event, now=datetime.now(UTC))
            output.update(status="eligible" if decision.allowed else "refused", reason=decision.reason)
            exit_code = 0 if decision.allowed else 2
        if args.install_url:
            output["install_url"] = installation_url(policy)
    except (OSError, ValueError, TypeError):
        # Validation errors can contain original input bytes, including a pasted
        # credential. Keep diagnostics content-free even for malformed documents.
        sys.stderr.write("Invalid or unreadable Reach preparation document.\n")
        return 1
    sys.stdout.write(json.dumps(output, sort_keys=True) + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
