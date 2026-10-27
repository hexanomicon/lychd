"""Explicit local Discord administration; chat cannot apply an operator plan."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import stat
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from lychd.compositions.reach.operator_wire import strict_json
from lychd.interface.discord.admin import (
    ServerPlan,
    apply_plan,
    developer_layout,
    plan_layout,
    snapshot_guild,
)
from lychd.interface.discord.operator_io import load_policy, read_token
from lychd.interface.discord.rest import DiscordRest, EffectJournal

MAX_PLAN_BYTES = 65_536


def load_plan(path: Path, expected_digest: str) -> ServerPlan:
    """Read the exact content-addressed plan, never a credential or executable file."""
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            msg = "plan_not_regular"
            raise ValueError(msg)
        raw = source.read(MAX_PLAN_BYTES + 1)
    if len(raw) > MAX_PLAN_BYTES:
        msg = "plan_too_large"
        raise ValueError(msg)
    envelope = strict_json(raw)
    if not isinstance(envelope, dict) or set(cast("dict[str, Any]", envelope)) != {"plan", "digest"}:
        msg = "plan_envelope"
        raise ValueError(msg)
    plan = ServerPlan.model_validate_json(json.dumps(envelope["plan"]))
    if envelope["digest"] != expected_digest or plan.digest != expected_digest:
        msg = "plan_digest_mismatch"
        raise ValueError(msg)
    return plan


async def run(args: argparse.Namespace) -> dict[str, Any]:
    policy = load_policy(args.policy)
    rest = DiscordRest(
        token=read_token(args.token_file),
        application_id=policy.application_id,
        bot_user_id=policy.bot_user_id,
        guild_id=policy.guild_id,
        journal=EffectJournal(args.effects_dir),
    )
    try:
        await rest.verify_identity()
        if args.command == "apply":
            plan = load_plan(args.plan, args.expect_digest)
            result = await apply_plan(rest, plan, expected_digest=args.expect_digest, now=datetime.now(UTC))
            return result.model_dump(mode="json")
        snapshot = await snapshot_guild(rest)
        if args.command == "inspect":
            return {"guild_id": policy.guild_id, "roles": len(snapshot.roles), "channels": len(snapshot.channels)}
        layout = developer_layout(
            application_id=policy.application_id,
            bot_user_id=policy.bot_user_id,
            guild_id=policy.guild_id,
            owner_id=args.owner_id,
            reach_channel_id=policy.allowed_channel_ids[0],
        )
        plan = plan_layout(layout, snapshot, now=datetime.now(UTC))
        return {"plan": plan.model_dump(mode="json"), "digest": plan.digest}
    finally:
        await rest.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--token-file", type=Path, required=True)
    parser.add_argument("--effects-dir", type=Path, required=True)
    commands_parser = parser.add_subparsers(dest="command", required=True)
    commands_parser.add_parser("inspect")
    plan_parser = commands_parser.add_parser("plan")
    plan_parser.add_argument("--owner-id", required=True)
    apply_parser = commands_parser.add_parser("apply")
    apply_parser.add_argument("--plan", type=Path, required=True)
    apply_parser.add_argument("--expect-digest", required=True)
    args = parser.parse_args(argv)
    previous_level = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        result = asyncio.run(run(args))
    except KeyboardInterrupt:
        return 130
    except Exception:  # noqa: BLE001 - fixed diagnostics must never echo an API token or body
        sys.stderr.write("reach_discord:operator_failed\n")
        return 1
    finally:
        logging.disable(previous_level)
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 0 if result.get("status") not in {"unknown", "rejected"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
