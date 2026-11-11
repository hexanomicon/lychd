"""Host UDP prerequisite only; all VPN authority remains in native Tether.

firewalld documents unbound interfaces as using the default zone:
https://firewalld.org/documentation/zone/default-zone.html
Only an existing zone and the normalized intent's exact UDP port are admitted.
"""

import hashlib
import ipaddress
import json
import os
import pwd
import re
import stat
import subprocess
import sys
from pathlib import Path

INTENT = Path("/home/lychd/.local/state/lychd-deploy/tether-intent.json")
LIMIT = 1024 * 1024


class PrerequisiteError(Exception):
    """A host prerequisite requires explicit operator correction."""


def require(condition, message):
    if not condition:
        raise PrerequisiteError(message)


def unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate public intent fields refused")
        result[key] = value
    return result


def trusted_tool(name):
    candidates = {
        "firewall-cmd": ("/usr/bin/firewall-cmd",),
        "ip": ("/usr/sbin/ip", "/usr/bin/ip"),
        "nmcli": ("/usr/bin/nmcli",),
    }
    for candidate in candidates[name]:
        path = Path(candidate)
        if not path.exists():
            continue
        path = path.resolve(strict=True)
        for item in (path, *path.parents):
            metadata = item.stat()
            require(
                metadata.st_uid == 0 and not metadata.st_mode & 0o022,
                "Host prerequisite tools must be root-owned and not group/world writable",
            )
        require(path.is_file() and os.access(path, os.X_OK), "Host prerequisite tool is not executable")
        return str(path)
    raise PrerequisiteError("Install the host firewalld, iproute2 and NetworkManager prerequisites first")


def run(tool, *args):
    result = subprocess.run(
        [trusted_tool(tool), *args],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env={"PATH": "/usr/sbin:/usr/bin", "LC_ALL": "C"},
    )
    require(
        len(result.stdout.encode()) <= LIMIT and len(result.stderr.encode()) <= LIMIT,
        "Host prerequisite observation exceeded its bound",
    )
    return result.returncode, result.stdout.strip()


def read_intent(expected_hash, path=INTENT, owner_uid=None):
    require(
        isinstance(expected_hash, str) and re.fullmatch("[0-9a-f]{64}", expected_hash),
        "A verified normalized campaign hash is required",
    )
    uid = pwd.getpwnam("lychd").pw_uid if owner_uid is None else owner_uid
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for part in path.parent.parts[1:]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
            metadata = os.fstat(descriptor)
            require(
                metadata.st_uid in {0, uid} and not metadata.st_mode & 0o022, "Public intent parent custody is unsafe"
            )
        file_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        try:
            metadata = os.fstat(file_fd)
            require(
                stat.S_ISREG(metadata.st_mode)
                and metadata.st_nlink == 1
                and metadata.st_uid == uid
                and stat.S_IMODE(metadata.st_mode) == 0o600
                and metadata.st_size <= LIMIT,
                "Public intent must be an ordinary private runtime-owned file",
            )
            raw = os.read(file_fd, LIMIT + 1)
            require(
                hashlib.sha256(raw).hexdigest() == expected_hash and len(raw) <= LIMIT,
                "Normalized public intent changed since campaign verification",
            )
            return json.loads(raw, object_pairs_hook=unique)
        finally:
            os.close(file_fd)
    finally:
        os.close(descriptor)


def reconcile(intent, zone, mode, command=run):
    require(mode in {"prepare", "plan", "verify"}, "Unsupported host prerequisite action")
    offered = intent["rune"].get("offered")
    if offered is None:
        return {"state": "not_required", "changed": False, "planned": []}
    require(
        isinstance(zone, str) and re.fullmatch("[A-Za-z0-9_-]{1,64}", zone),
        "Set lychd_tether_firewall_zone to the existing listener interface zone",
    )
    address = ipaddress.IPv4Address(offered["listen_address"])
    require(
        not (address.is_unspecified or address.is_loopback or address.is_multicast or address.is_link_local),
        "Choose one concrete assigned host IPv4 listener; wildcard/loopback/link-local listeners are not admitted",
    )
    port = offered["listen_port"]
    require(type(port) is int and 1 <= port <= 65535, "The normalized intent requires one numeric UDP port")

    def checked(tool, *args):
        code, output = command(tool, *args)
        require(code == 0, "Host address/firewalld prerequisite observation failed")
        return output

    def interface_zone():
        rows = json.loads(checked("ip", "-j", "-4", "address", "show"), object_pairs_hook=unique)
        matches = [
            row["ifname"]
            for row in rows
            for item in row.get("addr_info", [])
            if item.get("family") == "inet" and item.get("local") == str(address)
        ]
        require(len(matches) == 1, "Listener IPv4 must be assigned exactly once to one host interface")
        interface = matches[0]
        require(
            isinstance(interface, str) and re.fullmatch("[A-Za-z0-9_.:-]{1,15}", interface),
            "Host interface name is outside the closed prerequisite profile",
        )
        require(
            zone in checked("firewall-cmd", "--get-zones").split()
            and zone in checked("firewall-cmd", "--permanent", "--get-zones").split(),
            "Selected firewalld zone must already exist in runtime and permanent configuration",
        )
        for permanent in (False, True):
            prefix = ("--permanent",) if permanent else ()
            actual = checked("firewall-cmd", *prefix, "--get-zone-of-interface=" + interface)
            if actual in {"", "no zone"}:
                actual = checked("firewall-cmd", "--get-default-zone")
            require(actual == zone, "Listener interface runtime or permanent zone differs from selected firewalld zone")
        managed = checked("nmcli", "--get-values", "GENERAL.NM-MANAGED", "device", "show", interface)
        require(
            managed == "yes",
            "Only an observed NetworkManager-managed listener is supported; verify persistent ownership explicitly",
        )
        connection = checked("nmcli", "--get-values", "GENERAL.CON-UUID", "device", "show", interface)
        require(
            re.fullmatch("[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", connection),
            "Listener requires one active NetworkManager connection UUID",
        )
        saved_zone = checked("nmcli", "--get-values", "connection.zone", "connection", "show", "uuid", connection)
        if saved_zone == "":
            saved_zone = checked("firewall-cmd", "--get-default-zone")
        require(saved_zone == zone, "NetworkManager connection zone differs from selected firewalld zone")
        return interface

    interface = interface_zone()
    rule = str(port) + "/udp"
    missing = []
    for permanent in (True, False):
        prefix = ("--permanent",) if permanent else ()
        code, output = command("firewall-cmd", *prefix, "--zone=" + zone, "--query-port=" + rule)
        require((code, output) in {(0, "yes"), (1, "no")}, "Unable to query the exact firewalld UDP port")
        if code:
            missing.append(permanent)
    planned = ["permanent" if value else "runtime" for value in missing]
    require(mode != "verify" or not missing, "Required UDP port is missing from runtime or permanent firewalld")
    if mode == "prepare":
        for permanent in missing:
            require(interface_zone() == interface, "Listener interface changed before firewall preparation")
            prefix = ("--permanent",) if permanent else ()
            checked("firewall-cmd", *prefix, "--zone=" + zone, "--add-port=" + rule)
        # The verify path checks both exact port entries and the effective NIC zone again.
        reconcile(intent, zone, "verify", command)
    return {
        "state": "planned" if mode == "plan" and missing else "ready",
        "changed": mode == "prepare" and bool(missing),
        "planned": planned,
        "interface": interface,
        "zone": zone,
        "address": str(address),
        "port": port,
        "protocol": "udp",
        "provider_firewall": "not_observed",
    }


if __name__ == "__main__":
    try:
        require(os.geteuid() == 0, "Host firewall prerequisite requires the administrator connection")
        request = json.loads(sys.stdin.read(LIMIT + 1), object_pairs_hook=unique)
        require(set(request) == {"mode", "zone", "normalized_sha256"}, "Closed host prerequisite request required")
        result = reconcile(read_intent(request["normalized_sha256"]), request["zone"], request["mode"])
        print(json.dumps(result, sort_keys=True))
    except PrerequisiteError as error:
        sys.exit(str(error))
    except (OSError, ValueError, TypeError, KeyError, subprocess.SubprocessError):
        sys.exit("Host UDP prerequisite refused; verify the normalized intent and host firewalld installation")
