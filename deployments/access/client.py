"""Render private client files from trusted public server material; never change networking."""

import argparse
import base64
import ipaddress
import json
import os
import re
import stat
from pathlib import Path
from urllib.parse import urlsplit

FIELDS = {
    "schema_version",
    "interface",
    "server_address",
    "client_address",
    "endpoint",
    "server_wireguard_public_key",
    "server_ssh_host_key",
    "ssh_identity",
    "wireguard_private_key_file",
}
CONNECTION_FIELDS = {"schema_version", "interface", "server_address", "ssh_identity", "known_hosts"}
PRIVATE_NETWORKS = tuple(ipaddress.ip_network(value) for value in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def private_path(value):
    path = Path(value).expanduser()
    require(path.is_absolute(), "Use an absolute private path")
    require(
        not path.resolve().is_relative_to(Path(__file__).resolve().parents[2]),
        "Private client material must stay outside the source tree",
    )
    for candidate in (path, path.resolve()):
        require(
            not any((parent / ".git").exists() for parent in (candidate.parent, *candidate.parent.parents)),
            "Private client material must stay outside checkouts",
        )
    return path


def private_file(value, *, read=False):
    path = private_path(value)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as handle:
        info = os.fstat(handle.fileno())
        require(
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.getuid()
            and not info.st_mode & 0o077
            and info.st_nlink == 1,
            "Input must be a singly linked private regular file owned by this user",
        )
        if read:
            require(info.st_size <= 65536, "Private input exceeds the size limit")
            return handle.read().decode("utf-8")
    return str(path)


def address(value):
    require(isinstance(value, str), "A canonical private IPv4 address is required")
    result = ipaddress.IPv4Address(value)
    require(
        str(result) == value and any(result in network for network in PRIVATE_NETWORKS),
        "Use an explicit RFC1918 IPv4 address, without a prefix",
    )
    return str(result)


def interface(value):
    require(
        isinstance(value, str) and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,14}", value) and value != "lo",
        "Invalid WireGuard interface name",
    )
    return value


def key32(value):
    require(isinstance(value, str), "A canonical WireGuard key is required")
    try:
        decoded = base64.b64decode(value, validate=True)
    except ValueError:
        raise ValueError("Invalid WireGuard key encoding") from None
    require(
        len(decoded) == 32 and any(decoded) and base64.b64encode(decoded).decode() == value,
        "Invalid WireGuard key encoding",
    )
    return value


def ssh_host_key(value):
    require(isinstance(value, str) and "\n" not in value and "\r" not in value, "Invalid SSH host public key")
    parts = value.split()
    require(len(parts) >= 2 and parts[0] == "ssh-ed25519", "An independently verified ed25519 host key is required")
    try:
        wire = base64.b64decode(parts[1], validate=True)
    except ValueError:
        raise ValueError("Invalid SSH host public key") from None
    require(
        len(wire) == 51
        and wire[:19] == b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
        and any(wire[19:])
        and base64.b64encode(wire).decode() == parts[1],
        "Invalid SSH host public key",
    )
    return " ".join(parts[:2])


def endpoint(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9.\[\]:-]+", value), "Invalid WireGuard endpoint")
    parsed = urlsplit("//" + value)
    require(
        parsed.hostname and parsed.port and not parsed.username and not parsed.password and not parsed.path,
        "Endpoint must name a host and UDP port",
    )
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        labels = parsed.hostname.rstrip(".").split(".")
        require(
            len(parsed.hostname) <= 253
            and all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label) for label in labels),
            "Endpoint hostname is malformed",
        )
    require("replace" not in value.lower() and 1 <= parsed.port <= 65535, "Replace the endpoint placeholder")
    return value


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "Duplicate JSON field")
        result[key] = value
    return result


def load_connection(path):
    result = json.loads(private_file(path, read=True), object_pairs_hook=unique_object)
    require(
        isinstance(result, dict)
        and set(result) == CONNECTION_FIELDS
        and type(result["schema_version"]) is int
        and result["schema_version"] == 1,
        "Unsupported connection profile",
    )
    address(result["server_address"])
    interface(result["interface"])
    private_file(result["ssh_identity"])
    private_file(result["known_hosts"])
    return result


def render(config, output):
    require(
        isinstance(config, dict)
        and set(config) == FIELDS
        and type(config["schema_version"]) is int
        and config["schema_version"] == 1,
        "Supply exactly the documented client profile fields",
    )
    name = interface(config["interface"])
    server, peer = address(config["server_address"]), address(config["client_address"])
    require(server != peer, "Client and server addresses must differ")
    identity = private_file(config["ssh_identity"])
    private = key32(private_file(config["wireguard_private_key_file"], read=True).strip())
    public = key32(config["server_wireguard_public_key"])
    known = ssh_host_key(config["server_ssh_host_key"])
    remote = endpoint(config["endpoint"])
    connection = {
        "schema_version": 1,
        "interface": name,
        "server_address": server,
        "ssh_identity": identity,
        "known_hosts": str(output / "known_hosts"),
    }
    return {
        f"{name}.conf": f"[Interface]\nAddress = {peer}/32\nPrivateKey = {private}\n\n[Peer]\n"
        f"PublicKey = {public}\nEndpoint = {remote}\nAllowedIPs = {server}/32\n",
        "known_hosts": f"[{server}]:2222 {known}\n",
        "connection.json": json.dumps(connection, indent=2) + "\n",
    }


def prepare(config_path, output_path, *, check=False):
    output = private_path(output_path)
    config = json.loads(private_file(config_path, read=True), object_pairs_hook=unique_object)
    files = render(config, output)
    if os.path.lexists(output):
        info = output.lstat()
        require(
            stat.S_ISDIR(info.st_mode) and info.st_uid == os.getuid() and stat.S_IMODE(info.st_mode) == 0o700,
            "Output must be a private directory owned by this user",
        )
        require({path.name for path in output.iterdir()} == set(files), "Output directory is foreign or incomplete")
        require(
            all(private_file(output / name, read=True) == value for name, value in files.items()),
            "Existing client output differs; rotation requires a deliberate new profile",
        )
        return {"changed": False, "state": "unchanged", "directory": str(output)}
    if check:
        return {"changed": False, "state": "would_create", "files": sorted(files), "directory": str(output)}
    output.mkdir(mode=0o700)
    for name, content in files.items():
        with os.fdopen(
            os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "w"
        ) as handle:
            os.fchmod(handle.fileno(), 0o600)
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    return {"changed": True, "state": "created", "directory": str(output)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    parser.add_argument("--output-directory", required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = prepare(args.config, args.output_directory, check=args.check)
    except (OSError, ValueError, KeyError, TypeError):
        parser.error(
            "Client inputs or output refused; inspect private paths, exact fields and trusted public keys. No network was changed."
        )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
