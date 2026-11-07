"""Runtime-user classification, bounded configuration and acceptance for one LychD body.

Runs as the ordinary runtime account over direct SSH, never through sudo. One JSON object is
read from stdin and one JSON object is written to stdout:

- ``classify`` decides the only admitted next automation step, or refuses with exact reasons.
- ``configure`` replaces exactly the ``[server.web]`` image line of an unedited Codex.
- ``verify`` observes units, listener, authenticated API, database, storage and image identity.

The local access credential is read through ``lychd access`` into process memory, sent only to
the loopback Altar, and never written to output, arguments, files or exception text.
"""

import base64
import hashlib
import json
import os
import pwd
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

DEFAULT_IMAGE = "ghcr.io/hexanomicon/lychd:latest"
CORE_UNITS = ("lychd-pod.service", "lychd-phylactery.service", "lychd-reactor.path", "lychd-vessel.service")
OWNED_UNITS = (*CORE_UNITS, "lychd-migrate.service", "lychd-reactor.service")
UNIT_PROPERTIES = ("LoadState", "ActiveState", "SubState", "Result", "ExecMainStatus", "MainPID", "Job")
API_PATHS = ("/api/v1/altar/status", "/orchestrator/status", "/orchestrator/queues")
ALTAR_PORT = 7134
REVISION_LABEL = "org.opencontainers.image.revision"
TABLE = re.compile(r"^\s*\[([^\[\]]+)\]\s*(?:#.*)?$")
ARRAY_TABLE = re.compile(r"^\s*\[\[")
IMAGE_KEY = re.compile(r"^\s*image\s*=")
IMAGE_LINE = re.compile(r'^image = "([^"\\\s]+)"$')
SECRET_PREFIX = "lychd_"
QUIET_ENV = {"PYTHONDONTWRITEBYTECODE": "1", "LC_ALL": "C.UTF-8"}


class Refusal(Exception):
    """An observation that forbids the requested automation step."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def run(argv, *, timeout=60, cwd=None):
    """Run one bounded read-only command; the caller interprets the exit status."""
    env = dict(os.environ, **QUIET_ENV)
    try:
        return subprocess.run(argv, capture_output=True, text=True, timeout=timeout, cwd=cwd, env=env, check=False)
    except (OSError, subprocess.TimeoutExpired) as error:
        return subprocess.CompletedProcess(argv, 127, "", f"{type(error).__name__}")


class Layout:
    """Canonical runtime-account paths; XDG overrides are refused rather than guessed."""

    def __init__(self, home, revision):
        self.home = Path(home)
        self.revision = revision
        self.codex = self.home / ".config/lychd"
        self.crypt = self.home / ".local/share/lychd"
        self.cache = self.home / ".cache/lychd"
        self.quadlets = self.home / ".config/containers/systemd"
        self.user_units = self.home / ".config/systemd/user"
        self.settings = self.codex / "lychd.toml"
        self.receipt = self.codex / ".lychd-lifecycle.json"
        self.data = self.crypt / "postgres/data"
        self.source = self.home / "src" / f"lychd-{revision}"
        self.cli = self.source / ".venv/bin/lychd"
        self.image_ref = f"localhost/lychd:{revision}"


# ---------------------------------------------------------------- configuration


def server_web_image_lines(lines):
    """Return indexes of every ``image =`` key inside the ``[server.web]`` table."""
    section, hits = None, []
    for index, line in enumerate(lines):
        if ARRAY_TABLE.match(line):
            section = None
            continue
        table = TABLE.match(line)
        if table:
            section = table.group(1).strip()
            continue
        if section == "server.web" and IMAGE_KEY.match(line):
            hits.append(index)
    return hits


def config_state(text, receipt_digest):
    """Relate live settings to their creation digest through the one admitted edit."""
    lines = text.split("\n")
    hits = server_web_image_lines(lines)
    if len(hits) != 1:
        return {"state": "unknown_changes", "detail": f"{len(hits)} [server.web] image lines"}
    match = IMAGE_LINE.match(lines[hits[0]])
    if not match:
        return {"state": "unknown_changes", "detail": "[server.web] image line is not one plain string"}
    reverted = list(lines)
    reverted[hits[0]] = f'image = "{DEFAULT_IMAGE}"'
    digest = "sha256:" + hashlib.sha256("\n".join(reverted).encode()).hexdigest()
    if digest != receipt_digest:
        return {"state": "unknown_changes", "detail": "settings differ from creation beyond the image line"}
    image = match.group(1)
    return {"state": "pristine" if image == DEFAULT_IMAGE else "image_edit", "image": image, "line": hits[0] + 1}


def load_receipt(layout):
    receipt = json.loads(layout.receipt.read_text())
    require(receipt.get("version") == 2, "unsupported lifecycle receipt version")
    return receipt


def settings_digest(receipt, layout):
    digests = [item.get("digest") for item in receipt.get("files", []) if item.get("path") == str(layout.settings)]
    require(len(digests) == 1 and isinstance(digests[0], str), "lifecycle receipt does not name the settings file")
    return digests[0]


def parse_toml(text):
    import tomllib

    return tomllib.loads(text)


def extensions_are_empty(document):
    extensions = document.get("extensions", {})
    return extensions.get("builtins", []) == [] and extensions.get("crypt", []) == []


def configure(layout, request):
    """Replace exactly the image line of a pristine Codex, in place, preserving inode and mode."""
    expected_ref = request["image_ref"]
    require(expected_ref == layout.image_ref, "image reference must be the full-revision local tag")
    receipt = load_receipt(layout)
    digest = settings_digest(receipt, layout)
    before = layout.settings.stat()
    require(before.st_uid == os.getuid() and before.st_mode & 0o777 == 0o600, "settings must be private (0600)")
    with open(layout.settings, "r+b") as handle:
        original = handle.read().decode()
        state = config_state(original, digest)
        if state["state"] == "image_edit" and state["image"] == expected_ref:
            return {"changed": False, "config": state}
        require(state["state"] == "pristine", f"refusing to edit settings in state {state['state']}")
        lines = original.split("\n")
        lines[state["line"] - 1] = f'image = "{expected_ref}"'
        updated = "\n".join(lines)
        old_doc, new_doc = parse_toml(original), parse_toml(updated)
        old_doc["server"]["web"]["image"] = expected_ref
        require(old_doc == new_doc, "edit would change more than [server.web].image")
        require(extensions_are_empty(new_doc), "bounded trial requires empty builtins and crypt extensions")
        handle.seek(0)
        handle.write(updated.encode())
        handle.truncate()
        handle.flush()
        os.fsync(handle.fileno())
    after = layout.settings.stat()
    require((after.st_ino, after.st_dev) == (before.st_ino, before.st_dev), "settings inode changed")
    final = config_state(layout.settings.read_text(), digest)
    require(final.get("image") == expected_ref and final["state"] == "image_edit", "post-edit verification failed")
    return {"changed": True, "config": final}


# ---------------------------------------------------------------- observations


def unit_states(units=OWNED_UNITS):
    states = {}
    for unit in units:
        args = ["/usr/bin/systemctl", "--user", "show", unit] + [f"--property={name}" for name in UNIT_PROPERTIES]
        result = run(args)
        props = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
        states[unit] = props if result.returncode == 0 else {"error": f"rc={result.returncode}"}
    return states


def podman_lines(*args):
    result = run(["/usr/bin/podman", *args])
    require(result.returncode == 0, f"podman {args[0]} observation failed")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def footprint(layout):
    """Every LychD-owned name a fresh account must not already contain."""
    found = []
    for path in (layout.codex, layout.crypt, layout.cache):
        if os.path.lexists(path):
            found.append(str(path))
    for directory in (layout.quadlets, layout.user_units):
        if directory.is_dir():
            found.extend(str(path) for path in sorted(directory.glob("lychd*")))
    found.extend(
        f"secret:{name}"
        for name in podman_lines("secret", "ls", "--format", "{{.Name}}")
        if name.startswith(SECRET_PREFIX)
    )
    found.extend(
        f"container:{name}"
        for name in podman_lines("ps", "--all", "--format", "{{.Names}}")
        if name.startswith("lychd")
    )
    found.extend(
        f"pod:{name}" for name in podman_lines("pod", "ps", "--format", "{{.Name}}") if name.startswith("lychd")
    )
    return found


def cli_status(layout):
    require(layout.cli.is_file(), "the pinned revision's installed CLI is missing")
    result = run([str(layout.cli), "status", "--json"], cwd=layout.source, timeout=120)
    require(result.returncode == 0, f"lychd status --json exited {result.returncode}")
    document = json.loads(result.stdout)
    items = {item["name"]: item for item in document.get("items", []) if isinstance(item, dict) and "name" in item}
    return {
        "warnings": document.get("warnings", []),
        "items": {name: {"state": item.get("state"), "detail": item.get("detail")} for name, item in items.items()},
    }


def image_identity(reference):
    result = run(
        [
            "/usr/bin/podman",
            "image",
            "inspect",
            reference,
            "--format",
            '{{.Id}} {{index .Labels "' + REVISION_LABEL + '"}}',
        ]
    )
    if result.returncode != 0:
        return None
    image_id, _, revision = result.stdout.strip().partition(" ")
    return {"id": image_id, "revision": revision}


def quadlet_image(layout):
    path = layout.quadlets / "lychd-vessel.container"
    if not path.is_file():
        return None
    images = [line.split("=", 1)[1].strip() for line in path.read_text().splitlines() if line.startswith("Image=")]
    return images[0] if len(images) == 1 else None


def reactor_revisions(layout):
    path = layout.user_units / "lychd-reactor.service"
    if not path.is_file():
        return []
    return sorted(set(re.findall(r"/src/lychd-([0-9a-f]{40})/\.venv/bin/lychd", path.read_text())))


def data_is_empty(layout):
    if not os.path.lexists(layout.data):
        return True
    result = run(["/usr/bin/podman", "unshare", "/usr/bin/ls", "-A", str(layout.data)])
    require(result.returncode == 0, "PostgreSQL data directory could not be inspected")
    return not result.stdout.strip()


# ---------------------------------------------------------------- classification


def classify(layout, request):
    """Return exactly one admitted state; anything not proven safe is ``unknown``."""
    require(request["revision"] == layout.revision, "revision mismatch")
    units = unit_states()
    loaded = [unit for unit, props in units.items() if props.get("LoadState") not in (None, "not-found")]
    result = {"state": "unknown", "reasons": [], "units": units, "image_ref": layout.image_ref}
    reasons = result["reasons"]
    found = footprint(layout)
    result["footprint"] = found
    if not found and not loaded:
        result["state"] = "absent"
        return result

    foreign = [rev for rev in reactor_revisions(layout) if rev != layout.revision]
    if foreign:
        result["state"] = "foreign_revision"
        reasons.append(f"Host Reactor is bound to source revision {foreign[0]}")
        return result
    if not layout.receipt.is_file():
        reasons.append("LychD material exists without a lifecycle receipt; it is not adopted")
        return result
    receipt = load_receipt(layout)
    config = config_state(layout.settings.read_text(), settings_digest(receipt, layout))
    result["config"] = config
    status = cli_status(layout)
    result["status"] = status
    items = status["items"]
    state_of = {name: items.get(name, {}).get("state") for name in ("installation", "bindings", "services")}
    if status["warnings"]:
        reasons.append("lychd status reported warnings")
    if state_of["installation"] != "present":
        reasons.append(f"installation is {state_of['installation']}, not a validated lifecycle receipt")
    if config["state"] == "unknown_changes":
        reasons.append(f"settings: {config['detail']}")
    if reasons:
        return result

    configured_image = config["image"]
    identity = image_identity(configured_image) if config["state"] == "image_edit" else None
    result["configured_image"] = {"reference": configured_image, "identity": identity}
    if identity and identity["revision"] != layout.revision:
        result["state"] = "foreign_revision"
        reasons.append(
            f"configured image {configured_image} is labelled {identity['revision'] or 'without a revision'}"
        )
        return result

    if state_of["bindings"] == "absent":
        bound_names = [name for name in found if name.startswith(("container:", "pod:"))]
        if state_of["services"] != "absent" or bound_names or loaded:
            reasons.append("runtime units or containers exist without Scribe bindings")
        elif not data_is_empty(layout):
            reasons.append("PostgreSQL data exists without bindings; it is preserved and not adopted")
        elif config["state"] == "image_edit" and configured_image != layout.image_ref:
            reasons.append(f"settings name image {configured_image}, not {layout.image_ref}")
        else:
            result["state"] = "initialized"
        return result

    if state_of["bindings"] != "present":
        reasons.append(f"bindings are {state_of['bindings']}")
        return result
    if config["state"] != "image_edit" or identity is None:
        reasons.append("bound settings do not name an inspectable local image")
        return result
    if quadlet_image(layout) != configured_image:
        reasons.append("Vessel Quadlet image differs from settings; rebinding is an operator decision")
        return result
    if reactor_revisions(layout) != [layout.revision]:
        reasons.append("Host Reactor unit does not name the pinned source CLI")
        return result

    active = {unit: units[unit].get("ActiveState") for unit in CORE_UNITS}
    if all(state == "active" for state in active.values()) and state_of["services"] == "active":
        result["state"] = "running"
    elif all(state == "inactive" for state in active.values()) and not [
        name for name in podman_lines("ps", "--format", "{{.Names}}") if name.startswith("lychd")
    ]:
        if configured_image != layout.image_ref:
            reasons.append(f"inactive binding names {configured_image}; start is admitted only for {layout.image_ref}")
        else:
            result["state"] = "bound_inactive"
    else:
        reasons.append(f"core units are mixed or transitional: {active}")
    return result


# ---------------------------------------------------------------- acceptance


def listener_addresses(ss_output, port=ALTAR_PORT):
    addresses = []
    for line in ss_output.splitlines():
        fields = line.split()
        local = next((field for field in fields if field.endswith(f":{port}")), None)
        if local:
            addresses.append(local.rsplit(":", 1)[0].strip("[]"))
    return sorted(set(addresses))


def read_local_access(layout):
    """Return (url, basic-token); nothing derived from the password leaves this function in text."""
    result = run([str(layout.cli), "access"], cwd=layout.source)
    if result.returncode != 0:
        raise Refusal("lychd access refused")
    fields = dict(re.findall(r"^(Altar|Username|Password): (.*)$", result.stdout, re.M))
    if not {"Altar", "Username", "Password"} <= fields.keys():
        raise Refusal("lychd access output was not recognized")
    url = fields["Altar"].rstrip("/")
    require(re.fullmatch(rf"http://(127\.0\.0\.1|localhost):{ALTAR_PORT}", url), "Altar address is not loopback")
    token = base64.b64encode(f"{fields['Username']}:{fields['Password']}".encode()).decode()
    wrong = base64.b64encode(f"{fields['Username']}:wrong-{os.urandom(8).hex()}".encode()).decode()
    return url, token, wrong


def http_get(url, token=None):
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    if token:
        request.add_header("Authorization", "Basic " + token)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=20) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, b""
    except (urllib.error.URLError, OSError) as error:
        return 0, type(error).__name__.encode()


def api_checks(layout, http=http_get):
    checks = []
    try:
        base, token, wrong = read_local_access(layout)
    except Refusal as error:
        return [{"name": "api.access", "ok": False, "detail": str(error)}]
    bodies = {}
    for path in API_PATHS:
        anonymous, _ = http(base + path)
        refused, _ = http(base + path, wrong)
        status, body = http(base + path, token)
        ok = anonymous == 401 and refused == 401 and status == 200
        checks.append(
            {"name": f"api{path}", "ok": ok, "detail": f"anonymous={anonymous} wrong={refused} auth={status}"}
        )
        if status == 200:
            try:
                bodies[path] = json.loads(body)
            except ValueError:
                bodies[path] = None
    del token, wrong
    altar = bodies.get("/api/v1/altar/status") or {}
    checks.append(
        {
            "name": "api.database_readback",
            "ok": isinstance(altar.get("pending_consents"), int),
            "detail": f"pending_consents={altar.get('pending_consents')!r}",
        }
    )
    orchestrator = bodies.get("/orchestrator/status") or {}
    checks.append(
        {
            "name": "api.capabilities_empty",
            "ok": orchestrator.get("active_capabilities") == [] and orchestrator.get("all_capabilities") == [],
            "detail": f"active={orchestrator.get('active_capabilities')!r} containment={orchestrator.get('mutation_containment')!r}",
        }
    )
    queues = {row.get("name"): row for row in (bodies.get("/orchestrator/queues") or {}).get("queues", [])}
    idle = all(name in queues and queues[name].get("active") == 0 for name in ("runs", "rites"))
    checks.append(
        {
            "name": "api.queues_idle",
            "ok": idle,
            "detail": ", ".join(
                f"{name}:active={row.get('active')},depth={row.get('depth')}" for name, row in queues.items()
            ),
        }
    )
    return checks


PSQL = """
set -eu
U="${POSTGRES_USER:?}"
psql -U "$U" -d lychd -AtX -v ON_ERROR_STOP=1 -c "select count(*) from information_schema.tables where table_schema not in ('pg_catalog','information_schema')"
psql -U "$U" -d lychd -AtX -v ON_ERROR_STOP=1 -c "select rolname||':'||rolsuper from pg_roles where rolname in ('lychd_runtime','lychd_phoenix') order by 1"
"""


def database_checks():
    result = run(["/usr/bin/podman", "exec", "lychd-phylactery", "sh", "-c", PSQL])
    lines = result.stdout.split()
    tables = int(lines[0]) if result.returncode == 0 and lines and lines[0].isdigit() else 0
    roles = lines[1:]
    return [
        {"name": "database.tables", "ok": tables > 0, "detail": f"rc={result.returncode} tables={tables}"},
        {
            "name": "database.restricted_runtime_role",
            "ok": "lychd_runtime:false" in roles,
            "detail": " ".join(roles) or "absent",
        },
    ]


SUBVOL_INFO = """
import fcntl, os, struct, sys, uuid
fd = os.open(sys.argv[1], os.O_RDONLY | os.O_DIRECTORY)
buffer = bytearray(504)
fcntl.ioctl(fd, 0x81F8943C, buffer)
print(struct.unpack_from("<Q", buffer, 0)[0], uuid.UUID(bytes=bytes(buffer[296:312])))
"""


def storage_check(layout):
    mount = run(["/usr/bin/findmnt", "-n", "-o", "TARGET", "--mountpoint", str(layout.data)])
    if mount.returncode == 0 and mount.stdout.strip() == str(layout.data):
        return {"name": "storage.phylactery", "ok": True, "detail": "exact mountpoint"}
    receipt = load_receipt(layout)
    recorded = [item for item in receipt.get("subvolumes", []) if item.get("path") == str(layout.data)]
    if len(recorded) != 1:
        return {"name": "storage.phylactery", "ok": False, "detail": "neither a mountpoint nor a receipted subvolume"}
    live = run(["/usr/bin/podman", "unshare", "/usr/bin/python3", "-I", "-c", SUBVOL_INFO, str(layout.data)])
    observed = live.stdout.split()
    expected = [str(recorded[0].get("subvolume_id")), str(recorded[0].get("subvolume_uuid"))]
    inode = os.stat(layout.data).st_ino
    ok = live.returncode == 0 and observed == expected and inode == recorded[0].get("inode") == 256
    detail = f"receipted subvolume id={expected[0]} uuid={expected[1]}; live={' '.join(observed) or 'unreadable'} inode={inode}"
    return {"name": "storage.phylactery", "ok": ok, "detail": detail}


def verify(layout, request):
    checks = []
    units = unit_states()
    for unit in CORE_UNITS:
        state = units[unit].get("ActiveState")
        checks.append({"name": f"unit.{unit}", "ok": state == "active", "detail": state})
    migrate = units["lychd-migrate.service"]
    checks.append(
        {
            "name": "unit.lychd-migrate.service",
            "ok": migrate.get("Result") == "success" and migrate.get("ExecMainStatus") == "0",
            "detail": f"Result={migrate.get('Result')} ExecMainStatus={migrate.get('ExecMainStatus')}",
        }
    )
    status = cli_status(layout)
    items = status["items"]
    summary = {name: items.get(name, {}).get("state") for name in ("installation", "bindings", "services")}
    checks.append(
        {
            "name": "status.ownership",
            "ok": summary == {"installation": "present", "bindings": "present", "services": "active"}
            and not status["warnings"],
            "detail": f"{summary} warnings={len(status['warnings'])}",
        }
    )
    network = run(["/usr/bin/systemctl", "show", "network-online.target", "--property=ActiveState", "--value"])
    checks.append(
        {"name": "host.network-online", "ok": network.stdout.strip() == "active", "detail": network.stdout.strip()}
    )
    listeners = listener_addresses(run(["/usr/bin/ss", "-Hltn"]).stdout)
    checks.append(
        {
            "name": "listener.loopback_only",
            "ok": bool(listeners) and all(address in ("127.0.0.1", "::1") for address in listeners),
            "detail": ",".join(listeners) or "not listening",
        }
    )
    receipt = load_receipt(layout)
    config = config_state(layout.settings.read_text(), settings_digest(receipt, layout))
    configured = config.get("image")
    identity = image_identity(configured) if configured else None
    vessel = run(["/usr/bin/podman", "container", "inspect", "lychd-vessel", "--format", "{{.Image}}"]).stdout.strip()
    expected_id = request.get("image_id") or ""
    image_ok = bool(identity) and identity["revision"] == layout.revision and vessel == identity["id"]
    if expected_id:
        image_ok = image_ok and identity["id"] == expected_id
    checks.append(
        {
            "name": "image.identity",
            "ok": image_ok,
            "detail": f"settings={configured} id={identity and identity['id']} label={identity and identity['revision']} "
            f"vessel={vessel} artifact={expected_id or 'not required'}",
        }
    )
    checks.append(
        {"name": "config.single_image_edit", "ok": config["state"] == "image_edit", "detail": config["state"]}
    )
    if config["state"] == "image_edit":
        checks.append(
            {
                "name": "config.extensions_empty",
                "ok": extensions_are_empty(parse_toml(layout.settings.read_text())),
                "detail": "builtins/crypt",
            }
        )
    checks.append(
        {"name": "source.reactor_cli", "ok": reactor_revisions(layout) == [layout.revision], "detail": layout.revision}
    )
    checks.append(storage_check(layout))
    checks.extend(database_checks())
    checks.extend(api_checks(layout))
    return {"ok": all(check["ok"] for check in checks), "checks": checks}


def main():
    uid = os.getuid()
    account = pwd.getpwuid(uid)
    require(uid != 0 and account.pw_name == "lychd", "direct ordinary lychd login required")
    for name in ("XDG_CONFIG_HOME", "XDG_DATA_HOME", "XDG_CACHE_HOME"):
        value = os.environ.get(name)
        require(
            value
            in (
                None,
                "",
                str(
                    Path(account.pw_dir)
                    / {"XDG_CONFIG_HOME": ".config", "XDG_DATA_HOME": ".local/share", "XDG_CACHE_HOME": ".cache"}[name]
                ),
            ),
            f"{name} override is not supported",
        )
    command = sys.argv[1]
    request = json.loads(sys.stdin.read() or "{}")
    revision = request.get("revision", "")
    require(re.fullmatch(r"[0-9a-f]{40}", revision), "exact source SHA required")
    layout = Layout(account.pw_dir, revision)
    handlers = {"classify": classify, "configure": configure, "verify": verify}
    require(command in handlers, "unknown probe command")
    print(json.dumps(handlers[command](layout, request), sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (Refusal, ValueError, KeyError, OSError) as error:
        sys.exit(f"lychd application probe refused: {type(error).__name__}: {error}")
