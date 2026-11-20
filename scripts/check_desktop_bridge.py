"""Exercise real browser chat and recover the answer across a native restart in a fresh disposable OS account.

Install the project, PostgreSQL 18 with pgvector, a local llama-server, an instruct GGUF,
and Chrome (or Edge). On Linux, set LYCHD_VESSEL_MODE=native. Run with Python Playwright available:
    python scripts/check_desktop_bridge.py --engine PATH --model PATH --output NEW_DIRECTORY
The program installs the desktop profile into the fresh account and leaves the stopped data
directory in place. Its output contains screenshots of the synthetic conversation only.
"""

# ruff: noqa: S603 -- run the installed current-interpreter CLI on a disposable native host.
from __future__ import annotations

import argparse
import base64
import hashlib
import http.client
import json
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from http import HTTPStatus
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urljoin

import tomlkit
from check_desktop_startup import (
    check_password_rotation,
    check_registered_backup,
    check_routes,
    request,
    require_fresh_native_installation,
)

from lychd.domain.web.contracts import MessageAccepted, MessageIntent
from lychd.system.constants import PATH_SOULSTONES_DIR
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


def completed_reply(page: Page, run_id: str, screenshot: Path) -> str:
    turn = page.locator(
        f'article.turn--agent[data-run-id="{run_id}"]:is([data-state="done"],[data-state="failed"],[data-state="cancelled"])'
    )
    from playwright.sync_api import TimeoutError as BrowserTimeout

    try:
        turn.wait_for(timeout=240_000)
    except BrowserTimeout as exc:
        # Report only the public Run status from this synthetic trial.
        status = page.request.get(urljoin(page.url, f"/api/v1/orb/runs/{run_id}?after_seq=-1"))
        state = status.json()["run"]["status"] if status.ok else f"HTTP {status.status}"
        msg = f"Bridge Run {run_id} did not display a settled turn within four minutes (Orb: {state})."
        raise RuntimeError(msg) from exc
    state = turn.get_attribute("data-state")
    if state != "done":
        msg = f"Bridge Run {run_id} ended with state {state}."
        raise RuntimeError(msg)
    # A live terminal event can arrive before the persisted turn replaces it in the DOM.
    retained = turn.filter(has=page.get_by_text("Retained reply", exact=True))
    retained.wait_for(timeout=30_000)
    text = retained.locator(".turn__body").inner_text()
    capture(page, screenshot)
    if not re.search(r"\b19\b|\bnineteen\b", text, re.IGNORECASE):
        msg = f"Run {run_id} retained an incorrect response to the synthetic arithmetic prompt: {text[:200]!r}."
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


def switch_animators(page: Page, origin: str, output: Path) -> list[str]:
    """Use the Nexus UI to evict and launch both real processes, sharing one pinned GGUF."""
    page.goto(f"{origin}/nexus", wait_until="domcontentloaded")
    page.get_by_role("button", name="List", exact=True).click()
    transitions: list[str] = []
    for old, target, port in (("personal", "alternate", 8082), ("alternate", "personal", 8081)):
        key = f"{target}:chat:{target}-model"
        row = page.get_by_role("article").filter(
            has=page.get_by_role("button", name=f"Inspect managed capability {key}", exact=True)
        )
        with page.expect_response("**/api/v1/nexus/plan?*") as planned:
            row.get_by_role("button", name="Preview", exact=True).click()
        plan = planned.value.json()
        if plan["evict_coven_ids"] != [old] or plan["launch_coven_ids"] != [target]:
            msg = f"Nexus did not preview the exact {old} to {target} swap."
            raise RuntimeError(msg)
        with page.expect_response("**/api/v1/nexus/swaps") as submitted:
            page.get_by_role("button", name="Request transition", exact=True).click()
        if not submitted.value.ok:
            msg = f"Nexus rejected the transition to {target}."
            raise RuntimeError(msg)
        ticket = submitted.value.json()["ticket"]
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            observed = page.request.get(f"{origin}/api/v1/nexus/swaps/{ticket['id']}").json()["ticket"]
            if observed["phase"] == "completed":
                break
            if observed["phase"] in {
                "declined_no_effect",
                "failed_restored",
                "cancelled_restored",
                "contained_uncertain",
                "failed",
            }:
                msg = f"Nexus ended the {target} transition in {observed['phase']}."
                raise RuntimeError(msg)
            time.sleep(0.25)
        else:
            msg = f"Nexus did not complete the {target} transition."
            raise RuntimeError(msg)
        engine = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
        try:
            engine.request("GET", "/v1/models")
            response = engine.getresponse()
            if response.status != HTTPStatus.OK or f"{target}-model" not in {
                m["id"] for m in json.load(response)["data"]
            }:
                msg = f"The active loopback process did not serve {target}-model."
                raise RuntimeError(msg)
        finally:
            engine.close()
        transitions.append(ticket["request_id"])
    capture(page, output / "04-nexus.png")
    return transitions


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
    answer = completed_reply(page, run_id, output / "02-answer.png")
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
    from playwright.sync_api import sync_playwright

    require_fresh_native_installation(CLI)
    args.output.mkdir(parents=True, exist_ok=False)
    subprocess.run([*CLI, "desktop", "install"], check=True)
    try:
        subprocess.run([*CLI, "desktop", "install"], check=True)
        check_password_rotation(CLI)
        check_registered_backup(CLI)
        subprocess.run(
            [*CLI, "desktop", "configure-model", "--engine", str(args.engine), "--model", str(args.model)], check=True
        )
        # This disposable account owns the generated Rune. Bound a single arithmetic turn
        # through its public generation settings, leaving operator defaults unrestricted.
        rune = PATH_SOULSTONES_DIR / "llamacpp" / "personal.toml"
        config = tomlkit.parse(rune.read_text(encoding="utf-8"))
        config["generation"] = {"max_tokens": 128, "temperature": 0.0}
        rune.write_text(tomlkit.dumps(config), encoding="utf-8")
        # Distinct declared service, PID, port and served identity. The same verified weights
        # keep this trial focused on switching and avoid a second model download.
        config["name"] = "alternate"
        config["served_model_id"] = "alternate-model"
        config["port"] = 8082
        config["base_url"] = "http://127.0.0.1:8082/v1"
        rune.with_name("alternate.toml").write_text(tomlkit.dumps(config), encoding="utf-8")
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
        prompt = "What is 12 plus 7? Reply with just the number."
        with sync_playwright() as playwright:
            with session(), playwright.chromium.launch(channel=args.browser) as browser:
                page = browser.new_page(http_credentials=credentials, viewport={"width": 1440, "height": 960})
                check_routes(f"Basic {credential}")
                request_id, run_id, answer, conversation_url = offer(page, origin, prompt, args.output)
                transitions = switch_animators(page, origin, args.output)
            with session(), playwright.chromium.launch(channel=args.browser) as browser:
                page = browser.new_page(http_credentials=credentials, viewport={"width": 1440, "height": 960})
                page.goto(conversation_url, wait_until="domcontentloaded")
                page.get_by_text(prompt, exact=True).last.wait_for()
                if completed_reply(page, run_id, args.output / "03-restarted.png") != answer:
                    msg = "Retained answer differs after restart."
                    raise RuntimeError(msg)
                verify_dispatch(page, origin, run_id)
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
                "nexus_swap_request_ids": transitions,
                "max_tokens": 128,
                "temperature": 0.0,
            }
        (args.output / "receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    finally:
        subprocess.run([*CLI, "desktop", "stop"], check=True, timeout=60)


if __name__ == "__main__":
    main()
