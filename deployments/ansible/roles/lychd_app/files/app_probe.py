"""Protocol-1 JSON adapter for the already source-admitted ordinary-user CLI.

The controller owns source staging and protocol compatibility. LychD owns all
application paths, creation/binding proof, configuration, state and acceptance.
This stdlib-only helper never imports Core or interprets human command output.
"""

import json
import os
import pwd
import re
import subprocess
import sys
from pathlib import Path

SCHEMA = "lychd.deployment"
VERSION = 1
STATES = {"absent", "initialized", "bound_inactive", "running", "foreign_revision", "unknown"}
ACTIONS = {"absent": "init", "initialized": "bind", "bound_inactive": "start", "running": "observe"}


class Refusal(Exception):
    """An incompatible native response or invalid controller request."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def native_command(command, request, home):
    """Construct only the installed source's fixed native observation command."""
    revision = request.get("revision", "")
    require(re.fullmatch(r"[0-9a-f]{40}", revision), "exact source SHA required")
    require(command in {"classify", "verify"}, "unsupported observation")
    source = Path(home) / "src" / f"lychd-{revision}"
    argv = [str(source / ".venv/bin/lychd"), "status", "--json", "--deployment-revision", revision]
    identifier = request.get("image_id")
    if identifier:
        require(re.fullmatch(r"(?:sha256:)?[0-9a-f]{64}", identifier), "exact image ID required")
        argv.extend(["--deployment-image-id", identifier])
    if command == "verify":
        argv.append("--deployment-verify")
    return source, argv


def validate_response(document):
    """Require the exact native protocol without synthesizing lifecycle truth."""
    require(isinstance(document, dict), "native response is not an object")
    require(
        document.get("schema") == SCHEMA and type(document.get("version")) is int and document["version"] == VERSION,
        "native deployment protocol 1 required",
    )
    state = document.get("state")
    require(state in STATES, "unsupported native deployment state")
    require(document.get("next_action") == ACTIONS.get(state, "refuse"), "inconsistent native action")
    require(
        type(document.get("ok")) is bool
        and isinstance(document.get("reasons"), list)
        and isinstance(document.get("checks"), list),
        "incomplete native response",
    )
    return document


def observe(command, request, home):
    source, argv = native_command(command, request, home)
    require(Path(argv[0]).is_file(), "pinned native CLI is unavailable")
    try:
        result = subprocess.run(
            argv,
            cwd=source,
            env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1", LC_ALL="C.UTF-8"),
            capture_output=True,
            text=True,
            timeout=300,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise Refusal("native deployment observation unavailable") from error
    require(result.returncode in {0, 1}, "native deployment observation failed")
    try:
        document = validate_response(json.loads(result.stdout))
    except (ValueError, TypeError, KeyError) as error:
        raise Refusal("native deployment response unavailable or incompatible") from error
    require(document.get("revision", request["revision"]) == request["revision"], "native revision mismatch")
    return document, result.returncode


def main():
    uid = os.getuid()
    account = pwd.getpwuid(uid)
    require(uid != 0 and account.pw_name == "lychd", "direct ordinary lychd login required")
    request = json.loads(sys.stdin.read() or "{}")
    document, status = observe(sys.argv[1], request, account.pw_dir)
    print(json.dumps(document, sort_keys=True))
    return status


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (Refusal, ValueError, TypeError, KeyError, IndexError, OSError):
        sys.exit("lychd deployment protocol observation refused; matching controller and native protocol 1 required")
