#!/usr/bin/env python3
"""Render a reviewed fresh-install AutoYaST profile; never inspect or modify a target.

Only x86_64, one whole disk, BIOS Server or UEFI Server/KDE, and one wired network
are supported. Unknown intent refuses. XML generation is pure; the CLI reads only
the two named inputs and exclusively creates one private output file.
"""

from __future__ import annotations

import argparse
import base64
import binascii
import ipaddress
import json
import os
import re
import stat
import struct
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

NS = "http://www.suse.com/1.0/yast2ns"
CONFIG_NS = "http://www.suse.com/1.0/configns"
ET.register_namespace("", NS)
ET.register_namespace("config", CONFIG_NS)


class Refusal(ValueError):
    """An input cannot be represented by the supported installation contract."""


@dataclass(frozen=True)
class Network:
    interface: str
    mode: Literal["dhcp", "static"]
    address: str | None = None
    gateway: str | None = None
    nameservers: tuple[str, ...] = ()


@dataclass(frozen=True)
class Install:
    role: Literal["server", "workstation"]
    firmware: Literal["bios", "uefi"]
    disk: str
    hostname: str
    timezone: str
    keyboard: str
    swap_gib: int
    admin: str
    public_key: str
    network: Network


def fields(value: object, expected: set[str], label: str) -> dict:
    """Require an exact object shape, without printing input contents on failure."""
    if not isinstance(value, dict) or set(value) != expected:
        raise Refusal(f"{label}: fields must be exactly {', '.join(sorted(expected))}")
    return value


def text(value: object, pattern: str, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(pattern, value):
        raise Refusal(f"{label}: unsupported or malformed value")
    return value


def public_key(value: object) -> str:
    """Accept a plain Ed25519 public key, validating the SSH wire encoding."""
    value = text(value, r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}(?: [ -~]+)?", "public_key")
    try:
        blob = base64.b64decode(value.split()[1], validate=True)
        kind_length = struct.unpack(">I", blob[:4])[0]
        kind = blob[4 : 4 + kind_length]
        offset = 4 + kind_length
        key_length = struct.unpack(">I", blob[offset : offset + 4])[0]
        key = blob[offset + 4 :]
        if kind != b"ssh-ed25519" or key_length != 32 or len(key) != 32 or not any(key):
            raise ValueError
    except (ValueError, binascii.Error, struct.error):
        raise Refusal("public_key: invalid Ed25519 public key encoding") from None
    return value


def password_hash(value: str) -> str:
    """Accept SHA-512 crypt hashes, never plaintext, a lock marker or a placeholder."""
    value = value.removesuffix("\n")
    if not re.fullmatch(r"\$6\$(?:rounds=[1-9][0-9]{3,8}\$)?[./0-9A-Za-z]{1,16}\$[./0-9A-Za-z]{86}", value):
        raise Refusal("password hash must be a single SHA-512 crypt ($6$) hash")
    return value


def parse_network(value: object) -> Network:
    if not isinstance(value, dict) or value.get("mode") not in ("dhcp", "static"):
        raise Refusal("network.mode must be dhcp or static")
    expected = {"interface", "mode"}
    if value["mode"] == "static":
        expected |= {"address", "gateway", "nameservers"}
    data = fields(value, expected, "network")
    interface = text(data["interface"], r"[A-Za-z][A-Za-z0-9_-]{0,14}", "network.interface")
    if interface == "lo" or interface.startswith(("wl", "wlan")):
        raise Refusal("network.interface must identify a wired interface")
    if data["mode"] == "dhcp":
        return Network(interface, "dhcp")
    try:
        if not isinstance(data["address"], str) or "/" not in data["address"]:
            raise ValueError
        if not isinstance(data["gateway"], str):
            raise ValueError
        address = ipaddress.IPv4Interface(data["address"])
        gateway = ipaddress.IPv4Address(data["gateway"])
        raw_dns = data["nameservers"]
        if not isinstance(raw_dns, list) or not 1 <= len(raw_dns) <= 3:
            raise ValueError
        if any(not isinstance(item, str) for item in raw_dns):
            raise ValueError
        nameservers = tuple(str(ipaddress.IPv4Address(item)) for item in raw_dns)
        addresses = [address.ip, gateway, *(ipaddress.IPv4Address(item) for item in nameservers)]
        if any(
            item.is_unspecified or item.is_multicast or item.is_loopback or item.is_link_local for item in addresses
        ):
            raise ValueError
        if not 1 <= address.network.prefixlen <= 30:
            raise ValueError
        if gateway not in address.network or gateway == address.ip:
            raise ValueError
        if any(
            item in (address.network.network_address, address.network.broadcast_address)
            for item in (address.ip, gateway)
        ):
            raise ValueError
    except (ValueError, TypeError):
        raise Refusal(
            "network: require IPv4 /1..30, a distinct on-subnet gateway and 1..3 IPv4 DNS addresses"
        ) from None
    return Network(interface, "static", str(address), str(gateway), nameservers)


def parse_config(value: object) -> Install:
    data = fields(
        value,
        {
            "schema_version",
            "architecture",
            "role",
            "firmware",
            "disk",
            "hostname",
            "timezone",
            "keyboard",
            "swap_gib",
            "admin",
            "network",
        },
        "configuration",
    )
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise Refusal("schema_version must be integer 1")
    if data["architecture"] != "x86_64":
        raise Refusal("only x86_64 is supported")
    role = text(data["role"], r"server|workstation", "role")
    firmware = text(data["firmware"], r"bios|uefi", "firmware")
    if role == "workstation" and firmware != "uefi":
        raise Refusal("workstation profile requires UEFI")
    disk = fields(data["disk"], {"device", "erase_all"}, "disk")
    if disk["erase_all"] is not True:
        raise Refusal("disk.erase_all must explicitly be true; partition preservation is unsupported")
    device = text(disk["device"], r"/dev/(?:[sv]d[a-z]+|nvme[0-9]+n[0-9]+|disk/by-id/[A-Za-z0-9_.:+-]+)", "disk.device")
    if "replace" in device.lower() or device.endswith((".", "..")) or re.search(r"-part[0-9]+$", device):
        raise Refusal("disk.device must name a whole disk")
    hostname = text(data["hostname"], r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", "hostname")
    timezone = text(data["timezone"], r"[A-Za-z_+-]+(?:/[A-Za-z0-9_+-]+)*", "timezone")
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError:
        raise Refusal("timezone is not present in the controller's timezone database") from None
    keyboard = text(data["keyboard"], r"us|uk|de|fr|cz|sk", "keyboard")
    swap_gib = data["swap_gib"]
    if type(swap_gib) is not int or not 0 <= swap_gib <= 32:
        raise Refusal("swap_gib must be an integer from 0 to 32; hibernation is not configured")
    admin = fields(data["admin"], {"name", "public_key"}, "admin")
    name = text(admin["name"], r"[a-z][a-z0-9_]{0,30}", "admin.name")
    if name in {"root", "lychd", "nobody", "daemon", "bin", "mail", "wwwrun", "postgres", "sshd"}:
        raise Refusal("admin.name must be a distinct ordinary administrator, never the runtime account")
    return Install(
        role,
        firmware,
        device,
        hostname,
        timezone,
        keyboard,
        swap_gib,
        name,
        public_key(admin["public_key"]),
        parse_network(data["network"]),
    )


def element(parent: ET.Element, name: str, value: str | None = None, kind: str | None = None) -> ET.Element:
    child = ET.SubElement(parent, f"{{{NS}}}{name}")
    if kind:
        child.set(f"{{{CONFIG_NS}}}type", kind)
    child.text = value
    return child


def boolean(parent: ET.Element, name: str, value: bool) -> None:
    element(parent, name, "true" if value else "false", "boolean")


def values(parent: ET.Element, name: str, item: str, entries: tuple[str, ...] | list[str]) -> ET.Element:
    container = element(parent, name, kind="list")
    for entry in entries:
        element(container, item, entry)
    return container


def render(config: Install, secret_hash: str) -> bytes:
    """Produce deterministic XML. No input is interpreted as shell or XML markup."""
    secret_hash = password_hash(secret_hash)
    root = ET.Element(f"{{{NS}}}profile")
    general = element(root, "general")
    boolean(element(general, "mode"), "confirm", True)
    boolean(general, "self_update", False)
    element(element(root, "language"), "language", "en_US")
    element(element(root, "keyboard"), "keymap", config.keyboard)
    timezone = element(root, "timezone")
    element(timezone, "hwclock", "UTC")
    element(timezone, "timezone", config.timezone)

    drives = element(root, "partitioning", kind="list")
    drive = element(drives, "drive")
    element(drive, "device", config.disk)
    element(drive, "disklabel", "gpt")
    element(drive, "use", "all")
    boolean(drive, "initialize", True)
    boolean(drive, "enable_snapshots", True)
    partitions = element(drive, "partitions", kind="list")
    boot = element(partitions, "partition")
    boolean(boot, "create", True)
    element(boot, "partition_nr", "1", "integer")
    if config.firmware == "uefi":
        boolean(boot, "format", True)
        element(boot, "filesystem", "vfat", "symbol")
        element(boot, "mount", "/boot/efi")
        element(boot, "mountby", "uuid", "symbol")
        element(boot, "partition_id", "259", "integer")
        element(boot, "size", "1GiB")
    else:
        boolean(boot, "format", False)
        element(boot, "partition_id", "263", "integer")
        element(boot, "size", "8MiB")
    if config.swap_gib:
        swap = element(partitions, "partition")
        boolean(swap, "create", True)
        boolean(swap, "format", True)
        element(swap, "filesystem", "swap", "symbol")
        element(swap, "mount", "swap")
        element(swap, "size", f"{config.swap_gib}GiB")
    system = element(partitions, "partition")
    boolean(system, "create", True)
    boolean(system, "format", True)
    element(system, "filesystem", "btrfs", "symbol")
    element(system, "mount", "/")
    element(system, "mountby", "uuid", "symbol")
    element(system, "size", "max")
    element(system, "subvolumes_prefix", "@")
    boolean(system, "create_subvolumes", True)
    values(
        system,
        "subvolumes",
        "subvolume",
        ["home", "var", "opt", "srv", "root", "usr/local", "boot/grub2/i386-pc", "boot/grub2/x86_64-efi"],
    )
    loader = element(root, "bootloader")
    element(loader, "loader_type", "grub2-efi" if config.firmware == "uefi" else "grub2")
    loader_global = element(loader, "global")
    if config.firmware == "uefi":
        element(loader_global, "secure_boot", "true")
        element(loader_global, "update_nvram", "true")
    else:
        element(loader_global, "boot_mbr", "true")
        element(loader, "loader_device", config.disk)
    element(loader_global, "os_prober", "false")

    software = element(root, "software")
    values(software, "products", "product", ["openSUSE"])
    patterns = ["base", "enhanced_base", "yast2_basis", "selinux"]
    patterns += ["yast2_server"] if config.role == "server" else ["kde", "x11", "x11_yast"]
    values(software, "patterns", "pattern", patterns)
    packages = [
        "sudo",
        "openssh-server",
        "NetworkManager",
        "firewalld",
        "snapper",
        "btrfsprogs",
        "autoyast2",
        "yast2-security",
        "yast2-network",
        "yast2-users",
        "yast2-services-manager",
        "yast2-firewall",
    ]
    if config.role == "workstation":
        packages.append("sddm")
    values(software, "packages", "package", packages)
    boolean(software, "do_online_update", False)
    security = element(root, "security")
    element(security, "lsm_select", "selinux")
    element(security, "selinux_mode", "enforcing")

    network = element(root, "networking")
    element(network, "backend", "network_manager")
    boolean(network, "keep_install_network", False)
    interfaces = element(network, "interfaces", kind="list")
    interface = element(interfaces, "interface")
    element(interface, "name", config.network.interface)
    element(interface, "bootproto", config.network.mode)
    element(interface, "startmode", "auto")
    element(interface, "zone", "public")
    dns = element(network, "dns")
    element(dns, "hostname", config.hostname)
    boolean(dns, "dhcp_hostname", False)
    if config.network.mode == "static":
        element(interface, "ipaddr", config.network.address)
        values(dns, "nameservers", "nameserver", config.network.nameservers)
        routes = element(element(network, "routing"), "routes", kind="list")
        route = element(routes, "route")
        element(route, "destination", "default")
        element(route, "device", config.network.interface)
        element(route, "gateway", config.network.gateway)

    users = element(root, "users", kind="list")
    root_user = element(users, "user")
    element(root_user, "username", "root")
    element(root_user, "user_password", "!")
    boolean(root_user, "encrypted", True)
    admin = element(users, "user")
    element(admin, "username", config.admin)
    element(admin, "uid", "1000")
    element(admin, "home", f"/home/{config.admin}")
    element(admin, "shell", "/bin/bash")
    element(admin, "user_password", secret_hash)
    boolean(admin, "encrypted", True)
    values(admin, "authorized_keys", "listentry", [config.public_key])
    login = element(root, "login_settings")
    element(login, "autologin_user", "")
    boolean(login, "password_less_login", False)

    files = element(root, "files", kind="list")
    sudo = f"Defaults env_reset\nDefaults use_pty\nroot ALL=(ALL:ALL) ALL\n{config.admin} ALL=(ALL:ALL) ALL\n"
    # Fresh installation only: replacing the complete files avoids inherited broad
    # targetpw grants and sshd first-value-wins surprises from distribution includes.
    sshd = (
        "Port 22\nPermitRootLogin no\nPubkeyAuthentication yes\n"
        "PasswordAuthentication no\nKbdInteractiveAuthentication no\nUsePAM yes\n"
        "AuthorizedKeysFile .ssh/authorized_keys\nSubsystem sftp internal-sftp\n"
    )
    for path, contents, permissions in (("/etc/sudoers", sudo, "0440"), ("/etc/ssh/sshd_config", sshd, "0600")):
        item = element(files, "file")
        element(item, "file_path", path)
        element(item, "file_contents", contents)
        element(item, "file_owner", "root.root")
        element(item, "file_permissions", permissions)
    firewall = element(root, "firewall")
    boolean(firewall, "enable_firewall", True)
    boolean(firewall, "start_firewall", True)
    element(firewall, "default_zone", "public")
    zone = element(element(firewall, "zones", kind="list"), "zone")
    element(zone, "name", "public")
    values(zone, "interfaces", "interface", [config.network.interface])
    values(zone, "services", "service", ["ssh", "dhcpv6-client"])
    services = element(root, "services-manager")
    element(services, "default_target", "multi-user" if config.role == "server" else "graphical")
    enabled = ["NetworkManager", "sshd", "firewalld"]
    if config.role == "workstation":
        enabled.append("sddm")
    values(element(services, "services"), "enable", "service", enabled)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise Refusal("duplicate JSON object key")
        result[key] = value
    return result


def read_private_hash(path: Path) -> str:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "r", encoding="ascii") as source:
        info = os.fstat(source.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_mode & 0o077 or info.st_uid != os.geteuid():
            raise Refusal("password hash file must be a private regular file owned by the current user")
        return password_hash(source.read(1024))


def require_private_path(path: Path) -> None:
    """Reject repository ancestors by marker presence; do not read Git metadata."""
    if not path.is_absolute():
        raise Refusal("input and output paths must be absolute and outside repositories")
    for candidate in (path, path.resolve()):
        if any((parent / ".git").exists() for parent in candidate.parents):
            raise Refusal("input and output paths must be absolute and outside repositories")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--password-hash-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        for path in (args.config, args.password_hash_file, args.output):
            require_private_path(path)
        config = parse_config(json.loads(args.config.read_text(encoding="utf-8"), object_pairs_hook=unique_object))
        output = render(config, read_private_hash(args.password_hash_file))
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(output)
    except (Refusal, OSError, ValueError) as error:
        # JSON parsing exceptions contain positions, not the private input document.
        print(f"refused: {error}", file=sys.stderr)
        return 2
    print("Created private AutoYaST profile; review the installer proposal before erasing any disk.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
