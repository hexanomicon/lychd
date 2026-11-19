"""Operate one explicitly paired Intercom inbox using the installation's local credential."""

from __future__ import annotations

import argparse
import asyncio
import getpass
import hashlib
import json
import os
import ssl
import sys
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from lychd.db.intercom_inbox import MAX_RESULT_BYTES, InboxError, ReceiverInbox
from lychd.domain.codex.local_access import LocalOperatorAccess
from lychd.domain.intercom.transport import MAX_REQUEST_BYTES
from lychd.system.desktop.private import check_path, verify_private_directory, verify_private_file
from lychd.system.services.intercom_receiver import IntercomReceiver, PeerInvitation
from lychd.system.services.local_access import load_local_access


def _require_external(path: Path) -> None:
    if path.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        msg = "private-path"
        raise InboxError(msg)


def _read_config(path: Path) -> bytes:
    _require_external(path)
    verify_private_directory(path.parent)
    verify_private_file(path)
    with path.open("rb") as stream:
        raw = stream.read(MAX_REQUEST_BYTES + 1)
    if len(raw) > MAX_REQUEST_BYTES:
        msg = "config-size"
        raise InboxError(msg)
    return raw


async def _serve(pair: PeerInvitation, inbox: ReceiverInbox, authorize: Callable[[], None]) -> None:
    key = Path(os.environ["LYCHD_INTERCOM_SIGNING_KEY_FILE"])
    for path in (key, pair.tls_certificate, pair.tls_key):
        _require_external(path)
    verify_private_file(key)
    check_path(pair.tls_certificate)
    verify_private_file(pair.tls_key)
    tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls.minimum_version = ssl.TLSVersion.TLSv1_2
    tls.set_alpn_protocols(["http/1.1"])
    tls.load_cert_chain(pair.tls_certificate, pair.tls_key)
    receiver = IntercomReceiver(pair, inbox, key.read_bytes(), authorize)  # noqa: ASYNC240 - startup-only key
    await receiver.serve(tls)


async def run_session(
    config_path: Path, command: str, *, password: str, task: str | None = None, result: str | None = None
) -> object:
    """Recover only under a fresh operator login and the exact active invitation."""
    access = LocalOperatorAccess(access_password=load_local_access().password.get_secret_value())
    auth = access.authenticate(username=b"magus", password=password.encode())
    if auth is None:
        msg = "operator"
        raise InboxError(msg)
    original = _read_config(config_path)
    pair = PeerInvitation.model_validate_json(original)

    def authorize() -> None:
        try:
            active = (
                access.current(auth) and datetime.now(UTC) < pair.valid_until and _read_config(config_path) == original
            )
        except (ValueError, OSError):
            active = False
        if not active:
            access.revoke()
            msg = "invitation"
            raise InboxError(msg)

    authorize()
    # Renewing an intake window does not change the ownership of an admitted task.
    scope = pair.model_dump_json(exclude={"accept_from", "accept_until", "valid_until", "tls_certificate", "tls_key"})
    engine = create_async_engine(os.environ["LYCHD_INTERCOM_DATABASE_URL"], echo=False, hide_parameters=True)
    try:
        inbox = ReceiverInbox(
            async_sessionmaker(engine, expire_on_commit=False),
            peer=pair.sender_id,
            receiver=pair.receiver_id,
            task_schema=pair.task_schema,
            policy=hashlib.sha256(scope.encode()).hexdigest(),
        )
        if command == "serve":
            await _serve(pair, inbox, authorize)
            return None
        if command == "pending":
            return [asdict(item) for item in await inbox.pending(authorize=authorize)]
        if task is None:
            msg = "task"
            raise InboxError(msg)
        if command == "find":
            return asdict(await inbox.find(local_id=task, authorize=authorize))
        task_id = UUID(task)
        if command == "review":
            receipt, brief = await inbox.review(task_id=task_id, authorize=authorize)
            return {**asdict(receipt), "request_text": brief}
        states = {
            "start": "TASK_STATE_WORKING",
            "reject": "TASK_STATE_REJECTED",
            "complete": "TASK_STATE_COMPLETED",
        }
        receipt = await inbox.decide(
            task_id=task_id, state=states[command], result=result, authorize=authorize, check_start=pair.check_start
        )
        return asdict(receipt)
    finally:
        access.revoke()
        await engine.dispose()


def _public_result() -> str:
    raw = sys.stdin.buffer.read(MAX_RESULT_BYTES + 1)
    if len(raw) > MAX_RESULT_BYTES:
        msg = "result-size"
        raise InboxError(msg)
    return raw.decode("utf-8")


def main() -> None:
    """Run one locally authenticated operator action."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("serve", "pending", "find", "review", "start", "reject", "complete"):
        sub = commands.add_parser(name)
        if name not in {"serve", "pending"}:
            sub.add_argument("task", help="Original sender task ID for find. Use the receiver task UUID otherwise.")
        if name == "complete":
            sub.add_argument(
                "--public-result-stdin",
                action="store_true",
                required=True,
                help="Approve stdin as the public text reply.",
            )
    args = parser.parse_args()
    try:
        password = getpass.getpass("Dedicated local operator password: ")
        result = _public_result() if args.command == "complete" else None
        record = asyncio.run(
            run_session(args.config, args.command, password=password, task=getattr(args, "task", None), result=result)
        )
        if record is not None:
            print(json.dumps(record, default=str, ensure_ascii=True))  # noqa: T201 - explicit local output
    except InboxError as exc:
        parser.exit(1, f"Receiver refused: {exc.code}\n")
    except Exception:  # noqa: BLE001 - configuration, signing, DB and foreign material remain private
        parser.exit(1, "Receiver unavailable. Check the local invitation, keys and database migration.\n")


if __name__ == "__main__":
    main()
