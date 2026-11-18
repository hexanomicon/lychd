"""Exercise real browser chat and recover the answer across a native restart in a fresh disposable OS account.

Install the project, PostgreSQL 18 with pgvector, a local llama-server, an instruct GGUF,
and Chrome (or Edge). Run with Python Playwright available in the qualification environment:
    python scripts/check_desktop_bridge.py --engine PATH --model PATH --output NEW_DIRECTORY
The program installs the desktop profile into the fresh account and leaves the stopped data
directory in place. Its output contains screenshots of the synthetic conversation only.
"""

# ruff: noqa: S603 -- run the installed current-interpreter CLI on a disposable native host.
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING
from uuid import uuid4

from check_desktop_startup import check_registered_backup, check_routes, request

from lychd.domain.web.contracts import MessageAccepted, MessageIntent
from lychd.system.services.local_access import load_local_access

if TYPE_CHECKING:
    from collections.abc import Generator

    from playwright.sync_api import HttpCredentials, Page

CLI = [sys.executable, "-m", "lychd"]


@contextmanager
def session() -> Generator[None]:
    process = subprocess.Popen([*CLI, "desktop", "session"])
    try:
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline and process.poll() is None:
            try:
                if request("/api/v1/altar/status")[0] == HTTPStatus.UNAUTHORIZED:
                    break
            except OSError:
                pass
            time.sleep(0.2)
        else:
            msg = "Installed Vessel did not become ready."
            raise RuntimeError(msg)
        yield
    finally:
        try:
            if process.poll() is None:
                subprocess.run([*CLI, "stop"], check=True, timeout=100)
            if process.wait(timeout=30) != 0:
                msg = "Installed Vessel exited unsuccessfully."
                raise RuntimeError(msg)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=10)
            subprocess.run([*CLI, "desktop", "stop"], check=True, timeout=60)


def capture(page: Page, path: Path) -> None:
    # Page-only image, excluding browser chrome. No traces, headers, or browser state are saved.
    page.screenshot(path=path, mask=[page.locator('input[type="password"]')])


def completed_reply(page: Page, run_id: str) -> str:
    turn = page.locator(
        f'article.turn--agent[data-run-id="{run_id}"]:is([data-state="done"],[data-state="failed"],[data-state="cancelled"])'
    )
    turn.wait_for(timeout=240_000)
    state = turn.get_attribute("data-state")
    if state != "done":
        msg = f"Bridge Run {run_id} ended with state {state}."
        raise RuntimeError(msg)
    text = turn.locator(".turn__body").inner_text()
    if not re.search(r"\b19\b|\bnineteen\b", text, re.IGNORECASE):
        msg = "The completed model reply did not answer the arithmetic prompt."
        raise RuntimeError(msg)
    return text


def verify_dispatch(page: Page, origin: str, run_id: str) -> None:
    cursor = -1
    while True:
        response = page.request.get(f"{origin}/api/v1/orb/runs/{run_id}?after_seq={cursor}")
        snapshot = response.json()
        if snapshot["run"]["run_id"] != run_id:
            msg = "Orb returned a different Run."
            raise RuntimeError(msg)
        if any(
            row["kind"] == "dispatch"
            and row["animator_name"] == "personal"
            and row["model_id"] == "personal-model"
            and row["grant_id"]
            for row in snapshot["evidence"]
        ):
            return
        following = snapshot["next_after_seq"]
        if not snapshot["has_more"] or following is None or following <= cursor:
            msg = "The Run lacks retained dispatch evidence for the configured model."
            raise RuntimeError(msg)
        cursor = following


def offer(page: Page, origin: str, prompt: str, output: Path) -> tuple[str, str, str, str]:
    page.goto(f"{origin}/bridge", wait_until="domcontentloaded")
    begin = page.get_by_role("button", name="New Séance", exact=True)
    begin.wait_for()
    capture(page, output / "01-bridge.png")
    begin.click()
    page.get_by_role("textbox", name="Message").fill(prompt)
    with page.expect_response("**/api/v1/bridge/sessions/*/messages") as admitted:
        page.get_by_role("button", name="Offer", exact=True).click()
    response = admitted.value
    if not response.ok or response.request.method != "POST":
        msg = "Bridge refused the browser's message."
        raise RuntimeError(msg)
    receipt = MessageAccepted.model_validate(response.json())
    if (receipt.pattern_id, receipt.pattern_revision) != ("bridge_chat", "2"):
        msg = "Browser message was admitted on a different Pattern."
        raise RuntimeError(msg)
    intent = MessageIntent.model_validate(response.request.post_data_json)
    if intent.prompt != prompt:
        msg = "The admitted request differs from the browser prompt."
        raise RuntimeError(msg)
    request_id = str(intent.request_id)
    run_id = receipt.run_id
    if not re.fullmatch(r"[A-Za-z0-9_:.~-]+", run_id):
        msg = "Invalid admitted Run identity."
        raise RuntimeError(msg)
    answer = completed_reply(page, run_id)
    capture(page, output / "02-answer.png")
    conversation_url = page.url
    if not conversation_url.startswith(f"{origin}/bridge/"):
        msg = "No persistent Bridge conversation URL was selected."
        raise RuntimeError(msg)
    return request_id, run_id, answer, conversation_url


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--browser", choices=["chrome", "msedge"], default="chrome")
    return parser.parse_args()


def main() -> None:
    args = arguments()
    if sys.platform not in {"win32", "darwin"}:
        msg = "Use a fresh disposable Windows or macOS account."
        raise SystemExit(msg)
    from playwright.sync_api import sync_playwright

    profile = json.loads(subprocess.check_output([*CLI, "platform"], text=True))
    if profile["profile"] != "personal-desktop" or any(Path(profile[k]).exists() for k in ("data", "config")):
        msg = "A fresh disposable account with no existing LychD installation is required."
        raise SystemExit(msg)
    args.output.mkdir(parents=True, exist_ok=False)
    subprocess.run([*CLI, "desktop", "install"], check=True)
    try:
        subprocess.run([*CLI, "desktop", "install"], check=True)
        check_registered_backup(CLI)
        subprocess.run(
            [*CLI, "desktop", "configure-model", "--engine", str(args.engine), "--model", str(args.model)], check=True
        )
        access = load_local_access()
        credential = base64.b64encode(f"{access.username}:{access.password.get_secret_value()}".encode()).decode(
            "ascii"
        )
        origin = access.url.rstrip("/")
        credentials: HttpCredentials = {
            "username": access.username,
            "password": access.password.get_secret_value(),
            "origin": origin,
        }
        prompt = f"Trial {uuid4().hex[:8]}. What is 12 plus 7? Reply with the number."
        with sync_playwright() as playwright:
            with session(), playwright.chromium.launch(channel=args.browser) as browser:
                page = browser.new_page(http_credentials=credentials, viewport={"width": 1440, "height": 960})
                check_routes(f"Basic {credential}")
                request_id, run_id, answer, conversation_url = offer(page, origin, prompt, args.output)
            with session(), playwright.chromium.launch(channel=args.browser) as browser:
                page = browser.new_page(http_credentials=credentials, viewport={"width": 1440, "height": 960})
                page.goto(conversation_url, wait_until="domcontentloaded")
                page.get_by_text(prompt, exact=True).last.wait_for()
                if completed_reply(page, run_id) != answer:
                    msg = "Retained answer differs after restart."
                    raise RuntimeError(msg)
                verify_dispatch(page, origin, run_id)
                capture(page, args.output / "03-restarted.png")
        with args.model.open("rb") as model, args.engine.open("rb") as engine:
            result = {
                "model_sha256": hashlib.file_digest(model, "sha256").hexdigest(),
                "engine_sha256": hashlib.file_digest(engine, "sha256").hexdigest(),
                "request_id": request_id,
                "run_id": run_id,
                "conversation": conversation_url,
                "prompt": prompt,
                "retained_answer": answer,
                "platform": sys.platform,
            }
        (args.output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    finally:
        subprocess.run([*CLI, "desktop", "stop"], check=True, timeout=60)


if __name__ == "__main__":
    main()
