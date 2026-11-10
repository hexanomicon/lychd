"""Fresh-only host access candidate. Public stdin/output; private keys never leave the host.

Existing completed state is verified without mutation. Partial or changed state refuses;
revocation is durable and repeatable; there is no reconciliation, key rotation, or automatic recovery.
"""

import base64
import grp
import hashlib
import ipaddress
import json
import os
import pwd
import re
import shutil
import stat
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path("/etc/lychd-access")
WG = Path("/etc/wireguard/lychd-wg.conf")
UNIT = Path("/etc/systemd/system/lychd-access-sshd.service")
WG_DROPIN_DIR = Path("/etc/systemd/system/wg-quick@lychd-wg.service.d")
WG_DROPIN = WG_DROPIN_DIR / "10-lychd-access.conf"
RECEIPT = ROOT / "receipt.json"
REVOCATION = ROOT / "revoked.json"
ACCOUNT = "lychd-forward"
ZONE = "lychd-access"
INTERFACE = "lychd-wg"
UNITS = ("wg-quick@lychd-wg.service", "lychd-access-sshd.service")
PREPARE_RECEIPT = Path("/etc/lychd-access-prepare.json")
NM_CONFIG = Path("/etc/NetworkManager/conf.d/90-lychd-access.conf")
NM_CONTENT = "[device-lychd-access]\nmatch-device=interface-name:lychd-wg\nmanaged=0\n"
PACKAGES = (
    "wireguard-tools",
    "openssh-server",
    "firewalld",
    "policycoreutils",
    "policycoreutils-python-utils",
    "selinux-tools",
)


class Refusal(Exception):
    """An unknown boundary forbids mutation."""


def require(condition, message):
    if not condition:
        raise Refusal(message)


def run(args, *, data=None, allow_failure=False, timeout=60):
    result = subprocess.run(
        args,
        input=data,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LC_ALL": "C"},
    )
    require(allow_failure or result.returncode == 0, f"command refused: {args[0]}")
    return result


def validate(value):
    fields = {
        "server_address",
        "peer_address",
        "peer_public_key",
        "ssh_public_key",
        "external_interface",
        "external_zone",
        "udp_port",
    }
    require(isinstance(value, dict) and set(value) == fields, "supply exactly the documented public inputs")
    for name in ("server_address", "peer_address"):
        try:
            address = ipaddress.ip_interface(value[name])
        except (ValueError, TypeError):
            raise Refusal("invalid tunnel address") from None
        require(
            address.version == 4
            and address.network.prefixlen == 32
            and address.ip.is_private
            and not address.ip.is_loopback
            and not address.ip.is_link_local
            and not address.ip.is_unspecified
            and not address.ip.is_multicast
            and not address.ip.is_reserved,
            "only private unicast IPv4 /32 tunnel addresses are admitted",
        )
        require(str(address) == value[name], "use canonical /32 addresses")
    require(value["server_address"] != value["peer_address"], "tunnel addresses overlap")
    try:
        key = base64.b64decode(value["peer_public_key"], validate=True)
    except (ValueError, TypeError):
        raise Refusal("invalid WireGuard public key") from None
    require(
        len(key) == 32 and any(key) and base64.b64encode(key).decode() == value["peer_public_key"],
        "WireGuard public key must be canonical 32-byte base64",
    )
    require(
        isinstance(value["ssh_public_key"], str)
        and re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}", value["ssh_public_key"]),
        "supply one bare ed25519 SSH public key without options or comment",
    )
    try:
        encoded = value["ssh_public_key"].split(" ")[1]
        blob = base64.b64decode(encoded, validate=True)
    except (ValueError, TypeError):
        raise Refusal("invalid SSH public key encoding") from None
    # RFC 8709: two SSH strings, algorithm name and exactly 32 public-key octets.
    require(
        len(blob) == 51
        and blob[:19] == b"\x00\x00\x00\x0bssh-ed25519\x00\x00\x00\x20"
        and any(blob[19:])
        and base64.b64encode(blob).decode() == encoded,
        "invalid or zero ed25519 SSH public key wire format",
    )
    for name in ("external_interface", "external_zone"):
        require(
            isinstance(value[name], str) and re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,14}", value[name]),
            "invalid interface or zone",
        )
    require(
        value["external_interface"] != INTERFACE and value["external_zone"] != ZONE,
        "external and private network identities must differ",
    )
    require(type(value["udp_port"]) is int and 1024 <= value["udp_port"] <= 65535, "invalid UDP port")
    return value


def rules(intent):
    server = intent["server_address"].split("/")[0]
    peer = intent["peer_address"].split("/")[0]
    return (
        f'rule family="ipv4" port port="{intent["udp_port"]}" protocol="udp" accept',
        f'rule family="ipv4" source address="{peer}/32" destination address="{server}/32" '
        'port port="2222" protocol="tcp" accept',
    )


def render(intent, private_key):
    server = intent["server_address"].split("/")[0]
    return {
        WG: f"[Interface]\nAddress = {intent['server_address']}\nListenPort = {intent['udp_port']}\n"
        f"PrivateKey = {private_key}\n\n[Peer]\nPublicKey = {intent['peer_public_key']}\n"
        f"AllowedIPs = {intent['peer_address']}\n",
        ROOT / "authorized_keys": intent["ssh_public_key"] + "\n",
        ROOT / "sshd_config": f"""Port 2222
ListenAddress {server}
AddressFamily inet
HostKey /etc/lychd-access/ssh_host_ed25519_key
PidFile none
AuthorizedKeysFile /etc/lychd-access/authorized_keys
AllowUsers {ACCOUNT}
PermitRootLogin no
AuthenticationMethods publickey
PubkeyAuthentication yes
PasswordAuthentication no
KbdInteractiveAuthentication no
UsePAM yes
StrictModes yes
MaxSessions 0
AllowTcpForwarding local
PermitOpen 127.0.0.1:7134
PermitListen none
AllowStreamLocalForwarding no
AllowAgentForwarding no
X11Forwarding no
PermitTTY no
PermitTunnel no
PermitUserEnvironment no
GatewayPorts no
LogLevel VERBOSE
""",
        WG_DROPIN: "[Unit]\nBindsTo=firewalld.service\nAfter=firewalld.service\n"
        "ConditionPathExists=!/etc/lychd-access/revoked.json\n",
        UNIT: """[Unit]
Description=Candidate single-operator Altar forwarding transport
Requires=wg-quick@lychd-wg.service firewalld.service
BindsTo=wg-quick@lychd-wg.service firewalld.service
After=wg-quick@lychd-wg.service firewalld.service
ConditionPathExists=!/etc/lychd-access/revoked.json
[Service]
Type=simple
ExecStartPre=/usr/sbin/sshd -t -f /etc/lychd-access/sshd_config
ExecStart=/usr/sbin/sshd -D -e -f /etc/lychd-access/sshd_config
KillMode=control-group
Restart=no
[Install]
WantedBy=multi-user.target
""",
    }


def firewall(*args, permanent=False):
    query = any(arg.startswith("--query-") for arg in args)
    result = run(["firewall-cmd", *(["--permanent"] if permanent else []), *args], allow_failure=query)
    require(result.returncode in ((0, 1) if query else (0,)), "firewall observation failed")
    return result.stdout.strip()


GATEWAY_POLICIES = {
    # firewalld v2.5.2 config/policies/*.xml: all five have <disable/> and priority 1000.
    "gateway-dmz-to-HOST": ("CONTINUE", {"dmz"}, {"HOST"}, {"dhcp", "dns"}),
    "gateway-lan-to-HOST": ("CONTINUE", {"internal", "home", "trusted"}, {"HOST"}, {"dhcp", "dns", "ssh"}),
    "gateway-lan-to-work": ("ACCEPT", {"internal", "home", "trusted"}, {"work"}, {"ftp", "tftp"}),
    "gateway-lan-to-world": ("ACCEPT", {"internal", "home", "trusted"}, {"external", "public"}, {"ftp", "tftp"}),
    "gateway-world-to-HOST": ("CONTINUE", {"external", "public"}, {"HOST"}, {"dhcpv6-client"}),
}


def firewall_gateway_prerequisites(name, *, permanent):
    """Observe the exact disabled vendor object, never adopt an administrator override."""
    policy = "--policy=" + name
    # v2.5.2 FirewallCommand.print_zone_policy_info emits these fields once. Unlike
    # per-field invocations, one summary bounds watchdog observation overhead.
    lines = firewall(policy, "--list-all", permanent=permanent).splitlines()
    require(lines and lines[0] in (name, name + " (disabled)"), "gateway firewall policy header differs")
    fields = {}
    for line in lines[1:]:
        match = re.fullmatch(r"  ([a-z -]+):[ ]*(.*)", line)
        require(match is not None, "gateway firewall policy has malformed or extra content")
        field, value = match.groups()
        require(field not in fields, "gateway firewall policy has duplicate fields")
        fields[field] = value
    target, ingress, egress, services = GATEWAY_POLICIES[name]
    expected = {
        "disable": "yes",
        "priority": "1000",
        "target": target,
        "ingress-zones": ingress,
        "egress-zones": egress,
        "services": services,
        "ports": "",
        "protocols": "",
        "masquerade": "no",
        "forward-ports": "",
        "source-ports": "",
        "icmp-blocks": "",
        "rich rules": "",
    }
    require(set(fields) == set(expected), "gateway firewall policy fields differ")
    for field, value in expected.items():
        observed = fields[field]
        if isinstance(value, set):
            words = observed.split()
            require(len(words) == len(set(words)) and set(words) == value, "gateway firewall policy set differs")
        else:
            require(observed == value, "gateway firewall policy was changed or enabled")
    require(firewall(policy, "--query-disable", permanent=permanent) == "yes", "gateway firewall policy is enabled")
    if permanent:
        require(
            firewall("--path-policy=" + name, permanent=True) == f"/usr/lib/firewalld/policies/{name}.xml"
            and not os.path.lexists(f"/etc/firewalld/policies/{name}.xml"),
            "gateway firewall policy is not the vendor object",
        )


def firewall_policy_prerequisites():
    """Admit unchanged ICMPv6 bootstrap and exact disabled vendor gateway objects."""
    baseline = {"neighbour-advertisement", "neighbour-solicitation", "router-advertisement", "redirect"}
    full = baseline | {"mld-listener-done", "mld-listener-query", "mld-listener-report", "mld2-listener-report"}
    inventories = {}
    for permanent in (False, True):
        policies = firewall("--get-policies", permanent=permanent).split()
        require(len(policies) == len(set(policies)), "duplicate firewall policy objects")
        require(
            set(policies) <= {"allow-host-ipv6", *GATEWAY_POLICIES},
            "foreign firewall policy objects require separate review",
        )
        inventories[permanent] = set(policies)
    require(inventories[False] == inventories[True], "runtime and permanent firewall policy inventories differ")
    for permanent, policies in inventories.items():
        for name in sorted(policies & GATEWAY_POLICIES.keys()):
            firewall_gateway_prerequisites(name, permanent=permanent)
        if "allow-host-ipv6" not in policies:
            continue
        policy = "--policy=allow-host-ipv6"
        # Target/priority getters are permanent-only. Inspect actual runtime values via list-all.
        summary = firewall(policy, "--list-all", permanent=permanent)
        require(
            re.search(r"^\s*target: CONTINUE\s*$", summary, re.M)
            and re.search(r"^\s*priority: -15000\s*$", summary, re.M),
            "vendor IPv6 firewall target or priority differs",
        )
        for option, expected in {
            "list-ingress-zones": "ANY",
            "list-egress-zones": "HOST",
            "list-services": "",
            "list-ports": "",
            "list-protocols": "",
            "list-source-ports": "",
            "list-forward-ports": "",
            "list-icmp-blocks": "",
            "query-masquerade": "no",
            "query-disable": "no",
        }.items():
            require(
                firewall(policy, "--" + option, permanent=permanent) == expected,
                "vendor IPv6 firewall policy was changed",
            )
        observed = firewall(policy, "--list-rich-rules", permanent=permanent).splitlines()
        admitted = {f'rule family="ipv6" icmp-type name="{name}" accept' for name in full}
        require(
            set(observed) <= admitted
            and len(observed) == len(set(observed))
            and {line.split('name="')[1].split('"')[0] for line in observed} in (baseline, full),
            "vendor IPv6 firewall rules differ",
        )


def prerequisites(intent, existing):
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") != "lychd", "use the independent administrator")
    for executable in (
        "wg",
        "wg-quick",
        "sshd",
        "ssh-keygen",
        "firewall-cmd",
        "systemctl",
        "ip",
        "ss",
        "sudo",
        "useradd",
    ):
        require(shutil.which(executable), f"prerequisite executable missing: {executable}")
    for path in (Path("/etc"), Path("/etc/systemd/system"), WG.parent):
        if path.exists():
            info = path.lstat()
            require(
                stat.S_ISDIR(info.st_mode) and info.st_uid == 0 and not info.st_mode & 0o022,
                "configuration parents must be real root-owned directories",
            )
    require(
        'ID="opensuse-tumbleweed"' in Path("/etc/os-release").read_text()
        or "\nID=opensuse-tumbleweed\n" in Path("/etc/os-release").read_text(),
        "Tumbleweed host required",
    )
    require(
        Path("/proc/sys/net/ipv4/ip_forward").read_text().strip() == "0"
        and Path("/proc/sys/net/ipv6/conf/all/forwarding").read_text().strip() == "0",
        "host IP forwarding must already be disabled",
    )
    selinux_prerequisites(existing)
    if (
        shutil.which("nmcli")
        and run(["systemctl", "is-active", "NetworkManager.service"], allow_failure=True).returncode == 0
    ):
        for identifier in run(["nmcli", "-g", "UUID", "connection", "show"]).stdout.splitlines():
            managed_interface = run(
                ["nmcli", "-g", "connection.interface-name", "connection", "show", identifier]
            ).stdout.strip()
            require(managed_interface != INTERFACE, "NetworkManager already owns the interface")
        if existing:
            require(
                run(["nmcli", "-g", "GENERAL.NM-MANAGED", "device", "show", INTERFACE]).stdout.strip() == "no",
                "NetworkManager must report the existing WireGuard device unmanaged",
            )
    require(firewall("--state") == "running", "firewalld must be running")
    firewall_policy_prerequisites()
    for permanent in (False, True):
        require(
            not firewall("--direct", "--get-all-rules", permanent=permanent)
            and not firewall("--direct", "--get-all-passthroughs", permanent=permanent),
            "direct firewall rules require separate review",
        )
        zones = firewall("--get-zones", permanent=permanent).split()
        require(ZONE in zones and intent["external_zone"] in zones, "prepare the declared zones first")
        for zone in zones:
            require(
                not firewall(f"--zone={zone}", "--list-sources", permanent=permanent),
                "source-bound zones require separate review",
            )
        # --get-target is permanent-only; --list-all exposes the actual runtime target too.
        require(
            re.search(r"^\s*target: DROP\s*$", firewall(f"--zone={ZONE}", "--list-all", permanent=permanent), re.M),
            "private zone target must be DROP",
        )
        for option in ("services", "ports", "protocols", "source-ports", "forward-ports"):
            require(
                not firewall(f"--zone={ZONE}", f"--list-{option}", permanent=permanent),
                "private zone contains foreign permits",
            )
        require(
            firewall(f"--zone={ZONE}", "--query-masquerade", permanent=permanent) == "no",
            "private masquerading refused",
        )
        expected_interfaces = INTERFACE if existing else ""
        require(
            firewall(f"--zone={ZONE}", "--list-interfaces", permanent=permanent) == expected_interfaces,
            "private zone interface differs",
        )
        expected_rules = rules(intent)[1] if existing else ""
        require(
            firewall(f"--zone={ZONE}", "--list-rich-rules", permanent=permanent) == expected_rules,
            "private zone rules differ",
        )
    require(
        firewall(f"--get-zone-of-interface={intent['external_interface']}") == intent["external_zone"],
        "external interface zone differs",
    )


def private_write(path, text):
    # sshd opens AuthorizedKeysFile under the authenticating UID. Public key bytes must be
    # readable through the root-owned directory; private keys/configuration stay 0600.
    mode = 0o644 if path == ROOT / "authorized_keys" else 0o600
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, mode)
    os.fchmod(fd, mode)
    with os.fdopen(fd, "w") as handle:
        handle.write(text)
        handle.flush()
        os.fsync(handle.fileno())


def sync_directory(path):
    descriptor = os.open(path, os.O_DIRECTORY | os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def selinux_prerequisites(existing):
    """Observe an administrator-prepared enforcing policy; never relax or relabel foreign policy."""
    for executable in ("getenforce", "semanage", "matchpathcon", "restorecon"):
        require(shutil.which(executable), f"SELinux prerequisite missing: {executable}")
    require(run(["getenforce"]).stdout.strip() == "Enforcing", "this candidate requires SELinux Enforcing")
    ports = run(["semanage", "port", "-l"]).stdout
    require(ssh_port_admitted(ports), "administrator must admit TCP 2222 as ssh_port_t before installation")
    permissive = run(["semanage", "permissive", "-l"]).stdout
    require(not re.search(r"\bsshd(?:_[a-z]+)*_t\b", permissive), "permissive SSH domains refused")
    expected = {
        ROOT / "authorized_keys": "ssh_home_t",
        ROOT / "ssh_host_ed25519_key": "sshd_key_t",
        ROOT / "ssh_host_ed25519_key.pub": "sshd_key_t",
    }
    for path, expected_type in expected.items():
        context = run(["matchpathcon", "-n", str(path)]).stdout.strip().split(":")
        require(
            len(context) >= 3 and context[2] == expected_type,
            "administrator must prepare exact SSH file-context mappings before installation",
        )
    if existing:
        for path in (ROOT, *expected, ROOT / "sshd_config", WG, UNIT, WG_DROPIN_DIR, WG_DROPIN):
            run(["matchpathcon", "-V", str(path)])


def ssh_port_admitted(output):
    for line in output.splitlines():
        columns = line.split(None, 2)
        if len(columns) != 3 or columns[:2] != ["ssh_port_t", "tcp"]:
            continue
        for item in columns[2].split(","):
            # Require the explicit assignment documented for this profile. A broad range can
            # conceal a more-specific assignment to another type; it is not sufficient evidence.
            if item.strip() == "2222":
                return True
    return False


def digest(path):
    info = path.lstat()
    mode = 0o644 if path == ROOT / "authorized_keys" else 0o600
    require(
        stat.S_ISREG(info.st_mode) and info.st_uid == 0 and stat.S_IMODE(info.st_mode) == mode,
        "owned file type, owner, or mode differs",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def effective_ssh():
    run(["sshd", "-t", "-f", str(ROOT / "sshd_config")])
    restrictions = {
        "maxsessions": "0",
        "allowtcpforwarding": "local",
        "permitopen": "127.0.0.1:7134",
        "permitlisten": "none",
        "allowstreamlocalforwarding": "no",
        "passwordauthentication": "no",
        "kbdinteractiveauthentication": "no",
        "allowagentforwarding": "no",
        "x11forwarding": "no",
        "permittty": "no",
        "permittunnel": "no",
        "allowusers": ACCOUNT,
    }
    values = {}
    for line in run(["sshd", "-T", "-f", str(ROOT / "sshd_config")]).stdout.splitlines():
        parts = line.split(None, 1)
        if not parts:
            continue
        key = parts[0].lower()
        if key not in restrictions:
            # OpenSSH can legitimately repeat unrelated directives such as HostKey.
            continue
        require(len(parts) == 2 and parts[1].strip(), "effective SSH restriction has no value")
        require(key not in values, "effective SSH restriction is ambiguous")
        values[key] = parts[1].strip()
    for key, expected in restrictions.items():
        require(values.get(key) == expected, "effective SSH restrictions differ")


def verify(intent, receipt):
    require(
        receipt.get("intent") == intent and receipt.get("complete") is True,
        "partial or differing intent; recover manually",
    )
    for path, expected in receipt["files"].items():
        require(digest(Path(path)) == expected, "owned file changed; no automatic repair")
    prerequisites(intent, existing=True)
    effective_ssh()
    verify_units_owned()
    account = pwd.getpwnam(ACCOUNT)
    require(account.pw_uid == receipt["uid"] and account.pw_shell == "/usr/sbin/nologin", "forward account changed")
    sudo = run(["sudo", "-n", "-l", "-U", ACCOUNT], allow_failure=True)
    require(
        re.fullmatch(r"User lychd-forward is not allowed to run sudo on [^\n]+\.", (sudo.stdout + sudo.stderr).strip()),
        "forward account has sudo or ambiguous policy",
    )
    for unit in UNITS:
        require(
            run(["systemctl", "is-active", unit]).stdout.strip() == "active"
            and run(["systemctl", "is-enabled", unit]).stdout.strip() == "enabled",
            "owned unit inactive/disabled; refuse resurrection",
        )
    require(run(["wg", "show", INTERFACE, "peers"]).stdout.strip() == intent["peer_public_key"], "live peers differ")
    allowed = run(["wg", "show", INTERFACE, "allowed-ips"]).stdout.split()
    require(allowed == [intent["peer_public_key"], intent["peer_address"]], "live peer routes differ")
    require(
        run(["wg", "show", INTERFACE, "listen-port"]).stdout.strip() == str(intent["udp_port"]), "live UDP port differs"
    )
    require(
        run(["wg", "show", INTERFACE, "public-key"]).stdout.strip() == receipt["public"]["wireguard_public_key"],
        "live WireGuard identity differs",
    )
    addresses = json.loads(run(["ip", "-j", "address", "show", "dev", INTERFACE]).stdout)
    live = [
        (item["family"], item["local"], item["prefixlen"]) for link in addresses for item in link.get("addr_info", [])
    ]
    require(live == [("inet", intent["server_address"].split("/")[0], 32)], "live interface addresses differ")
    listeners = [
        field for row in run(["ss", "-Hltn"]).stdout.splitlines() for field in row.split() if field.endswith(":2222")
    ]
    require(listeners == [intent["server_address"].split("/")[0] + ":2222"], "SSH listener boundary differs")
    for permanent in (False, True):
        require(
            rules(intent)[0]
            in firewall(f"--zone={intent['external_zone']}", "--list-rich-rules", permanent=permanent).splitlines(),
            "external UDP rule missing",
        )


def load_owned_receipt(intent):
    root_info = ROOT.lstat()
    require(
        stat.S_ISDIR(root_info.st_mode) and root_info.st_uid == 0 and stat.S_IMODE(root_info.st_mode) == 0o711,
        "access root must be a root-owned 0711 directory",
    )
    digest(RECEIPT)
    receipt = json.loads(RECEIPT.read_text())
    require(receipt.get("intent") == intent and receipt.get("complete") is True, "partial or differing intent")
    expected = {*render(intent, ""), ROOT / "ssh_host_ed25519_key", ROOT / "ssh_host_ed25519_key.pub"}
    require(set(receipt.get("files", {})) == {str(path) for path in expected}, "owned receipt file set differs")
    for path, expected_digest in receipt["files"].items():
        require(digest(Path(path)) == expected_digest, "owned file changed; no automatic repair")
    return receipt


def verify_units_owned(*, fresh=False, allow_missing_wireguard=False):
    if fresh:
        require(not os.path.lexists(WG_DROPIN_DIR), "foreign or partial WireGuard drop-in directory")
    else:
        directory = WG_DROPIN_DIR.lstat()
        require(
            stat.S_ISDIR(directory.st_mode) and directory.st_uid == 0 and stat.S_IMODE(directory.st_mode) == 0o755,
            "WireGuard drop-in directory must be a real root-owned 0755 directory",
        )
    for unit, expected_fragment in (
        (UNITS[0], "/usr/lib/systemd/system/wg-quick@.service"),
        (UNITS[1], str(UNIT)),
    ):
        expected_dropins = [str(WG_DROPIN)] if not fresh and unit == UNITS[0] else []
        observed_dropins = run(
            ["systemctl", "show", unit, "--property=DropInPaths", "--value"], allow_failure=fresh
        ).stdout.split()
        require(observed_dropins == expected_dropins, "foreign or missing unit drop-ins refused")
        fragment = run(
            ["systemctl", "show", unit, "--property=FragmentPath", "--value"], allow_failure=fresh
        ).stdout.strip()
        expected = {expected_fragment}
        if fresh and unit == UNITS[1]:
            expected = {""}
        if allow_missing_wireguard and unit == UNITS[0]:
            expected.add("")
        require(fragment in expected, "foreign unit fragment refused")


def verify_revoked(intent):
    digest(REVOCATION)
    require(json.loads(REVOCATION.read_text()) == {"revoked": True, "intent": intent}, "revocation intent differs")
    for unit in UNITS:
        require(
            run(["systemctl", "is-active", unit], allow_failure=True).stdout.strip() == "inactive"
            and run(["systemctl", "is-enabled", unit], allow_failure=True).stdout.strip() == "disabled",
            "transport revocation pending; repeat explicit revoke",
        )
    links = json.loads(run(["ip", "-j", "link", "show"]).stdout)
    require(not any(link.get("ifname") == INTERFACE for link in links), "revoked interface still exists")


def revoke(intent, *, plan=False):
    """Persist the fence first, then finish stopping only this receipt's dedicated transport."""
    intent = validate(intent)
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") != "lychd", "use the independent administrator")
    load_owned_receipt(intent)
    verify_units_owned()
    existing = os.path.lexists(REVOCATION)
    if existing:
        digest(REVOCATION)
        require(json.loads(REVOCATION.read_text()) == {"revoked": True, "intent": intent}, "revocation intent differs")
        try:
            verify_revoked(intent)
        except Refusal:
            pass
        else:
            return {"changed": False, "state": "revoked"}
    if plan:
        return {"changed": False, "state": "revocation_candidate", "would_revoke": True}
    if not existing:
        private_write(REVOCATION, json.dumps({"revoked": True, "intent": intent}, sort_keys=True) + "\n")
        sync_directory(ROOT)
    run(["systemctl", "disable", "--now", UNITS[1], UNITS[0]])
    verify_revoked(intent)
    return {"changed": True, "state": "revoked"}


def operate(action, intent):
    intent = validate(intent)
    require(action in ("plan", "apply", "verify"), "unknown action")
    if ROOT.exists() or ROOT.is_symlink():
        receipt = load_owned_receipt(intent)
        if os.path.lexists(REVOCATION):
            require(action == "verify", "transport was revoked; installation cannot resurrect it")
            verify_units_owned()
            verify_revoked(intent)
            return {"changed": False, "state": "revoked"}
        verify(intent, receipt)
        return {"changed": False, "state": "verified", **receipt["public"]}
    require(action != "verify", "no completed installation to verify")
    prerequisites(intent, existing=False)
    verify_units_owned(fresh=True)
    for path in (WG, UNIT, WG_DROPIN_DIR):
        require(not os.path.lexists(path), "foreign access path exists")
    require(not run(["ip", "link", "show", INTERFACE], allow_failure=True).returncode == 0, "foreign interface exists")
    routes = json.loads(run(["ip", "-j", "-4", "route", "show", "table", "all"]).stdout)
    for route in routes:
        destination = route.get("dst", "default")
        if destination != "default":
            network = ipaddress.ip_network(destination, strict=False)
            require(
                not any(
                    ipaddress.ip_interface(intent[key]).ip in network for key in ("server_address", "peer_address")
                ),
                "tunnel addresses overlap an existing route",
            )
    try:
        pwd.getpwnam(ACCOUNT)
    except KeyError:
        pass
    else:
        raise Refusal("foreign forwarding account exists")
    try:
        grp.getgrnam(ACCOUNT)
    except KeyError:
        pass
    else:
        raise Refusal("foreign forwarding group exists")
    listeners = run(["ss", "-Hlun"]).stdout.splitlines()
    require(
        not any(any(field.endswith(":" + str(intent["udp_port"])) for field in row.split()) for row in listeners),
        "UDP port already in use",
    )
    require(
        not any(
            any(field.endswith(":2222") for field in row.split()) for row in run(["ss", "-Hltn"]).stdout.splitlines()
        ),
        "SSH transport port already in use",
    )
    for permanent in (False, True):
        require(
            rules(intent)[0]
            not in firewall(f"--zone={intent['external_zone']}", "--list-rich-rules", permanent=permanent).splitlines(),
            "declared UDP rule already exists without ownership",
        )
    if action == "plan":
        return {"changed": False, "state": "fresh_candidate", "would_install": True}
    ROOT.mkdir(mode=0o711)
    ROOT.chmod(0o711)
    # Presence of ROOT fences interrupted setup. Never remove it automatically after failure.
    private = run(["wg", "genkey"]).stdout.strip()
    public = run(["wg", "pubkey"], data=private + "\n").stdout.strip()
    new_wg_parent = not WG.parent.exists()
    WG.parent.mkdir(mode=0o700, exist_ok=True)
    if new_wg_parent:
        run(["restorecon", str(WG.parent)])
    else:
        run(["matchpathcon", "-V", str(WG.parent)])
    WG_DROPIN_DIR.mkdir(mode=0o755)
    WG_DROPIN_DIR.chmod(0o755)
    run(["restorecon", str(WG_DROPIN_DIR)])
    run(["matchpathcon", "-V", str(WG_DROPIN_DIR)])
    files = render(intent, private)
    del private
    for path, content in files.items():
        private_write(path, content)
    run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(ROOT / "ssh_host_ed25519_key")])
    # Public key file also stays root-only so the complete owned set has one mode contract.
    (ROOT / "ssh_host_ed25519_key.pub").chmod(0o600)
    for path in (ROOT, *files, ROOT / "ssh_host_ed25519_key", ROOT / "ssh_host_ed25519_key.pub"):
        run(["restorecon", str(path)])
        run(["matchpathcon", "-V", str(path)])
    run(["ssh-keygen", "-l", "-f", str(ROOT / "authorized_keys")])
    effective_ssh()
    run(
        [
            "useradd",
            "--system",
            "--user-group",
            "--no-create-home",
            "--home-dir",
            "/var/empty",
            "--shell",
            "/usr/sbin/nologin",
            "--password",
            "*",
            ACCOUNT,
        ]
    )
    sudo = run(["sudo", "-n", "-l", "-U", ACCOUNT], allow_failure=True)
    require(
        re.fullmatch(r"User lychd-forward is not allowed to run sudo on [^\n]+\.", (sudo.stdout + sudo.stderr).strip()),
        "forward account has sudo or ambiguous policy",
    )
    for permanent in (True, False):
        firewall(f"--zone={ZONE}", f"--add-rich-rule={rules(intent)[1]}", permanent=permanent)
        firewall(f"--zone={ZONE}", f"--add-interface={INTERFACE}", permanent=permanent)
        firewall(f"--zone={intent['external_zone']}", f"--add-rich-rule={rules(intent)[0]}", permanent=permanent)
    # Persist the instance boot fence before either transport may be enabled.
    sync_directory(WG_DROPIN_DIR)
    sync_directory(WG_DROPIN_DIR.parent)
    run(["systemctl", "daemon-reload"])
    for unit in UNITS:
        run(["systemctl", "enable", "--now", unit])
    # Type=simple does not signal listener readiness. Poll observations only on fresh activation.
    deadline = time.monotonic() + 15
    expected_listener = intent["server_address"].split("/")[0] + ":2222"
    while not any(expected_listener in row.split() for row in run(["ss", "-Hltn"]).stdout.splitlines()):
        require(time.monotonic() < deadline, "new SSH transport listener did not become ready")
        time.sleep(0.1)
    owned = [*files, ROOT / "ssh_host_ed25519_key", ROOT / "ssh_host_ed25519_key.pub"]
    receipt = {
        "complete": True,
        "intent": intent,
        "uid": pwd.getpwnam(ACCOUNT).pw_uid,
        "files": {str(path): digest(path) for path in owned},
        "public": {
            "wireguard_public_key": public,
            "ssh_host_public_key": (ROOT / "ssh_host_ed25519_key.pub").read_text().strip(),
        },
    }
    verify(intent, receipt)
    private_write(RECEIPT, json.dumps(receipt, sort_keys=True) + "\n")
    return {"changed": True, "state": "candidate_installed", **receipt["public"]}


def exact_port_conflict(output, include_ranges=False):
    for line in output.splitlines():
        columns = line.split(None, 2)
        if len(columns) == 3 and columns[1] == "tcp" and columns[0] != "ssh_port_t":
            for item in columns[2].split(","):
                bounds = item.strip().split("-")
                if bounds == ["2222"]:
                    return True
                if include_ranges and len(bounds) == 2 and all(part.isdigit() for part in bounds):
                    if int(bounds[0]) <= 2222 <= int(bounds[1]):
                        return True
    return False


def custom_context_conflict(output, path, expected):
    for line in output.splitlines():
        columns = line.split()
        if not columns or not columns[0].startswith("/"):
            continue
        try:
            matches = re.fullmatch(columns[0], path)
        except re.error:
            raise Refusal("unparseable local SELinux file-context rule") from None
        if matches and (len(columns[-1].split(":")) < 3 or columns[-1].split(":")[2] != expected):
            return True
    return False


def prepare(action, intent):
    """Explicit pilot bootstrap. Add absent intent only; never repair partial or conflicting state."""
    intent = validate(intent)
    require(action in ("prepare-plan", "prepare-apply"), "unknown preparation action")
    require(os.geteuid() == 0 and os.environ.get("SUDO_USER") != "lychd", "use the independent administrator")
    if ROOT.exists() or ROOT.is_symlink():
        return operate("plan", intent)
    require("opensuse-tumbleweed" in Path("/etc/os-release").read_text(), "Tumbleweed host required")
    require(Path("/sys/fs/selinux/enforce").read_text().strip() == "1", "SELinux must already enforce")
    if os.path.lexists(PREPARE_RECEIPT):
        digest(PREPARE_RECEIPT)
        receipt = json.loads(PREPARE_RECEIPT.read_text())
        require(receipt == {"complete": True, "intent": intent}, "partial or differing preparation; recover manually")
        require(NM_CONFIG.read_text() == NM_CONTENT, "owned NetworkManager reservation changed")
        prerequisites(intent, existing=False)
        return {"changed": False, "state": "prerequisites_verified"}
    require(not os.path.lexists(NM_CONFIG), "foreign NetworkManager reservation exists")
    require(
        NM_CONFIG.parent.is_dir() and not NM_CONFIG.parent.is_symlink(),
        "NetworkManager configuration directory missing/unsafe",
    )
    # The host floor already owns the network managers. Never enable a new firewall or take
    # over a foreign interface merely to make prerequisite automation convenient.
    for unit in ("NetworkManager.service", "firewalld.service"):
        require(
            run(["systemctl", "is-active", unit], allow_failure=True).returncode == 0,
            "preparation requires existing active NetworkManager and firewalld",
        )
    for path in (WG, UNIT, WG_DROPIN_DIR):
        require(not os.path.lexists(path), "foreign access path exists before preparation")
    require(
        run(["ip", "link", "show", INTERFACE], allow_failure=True).returncode != 0,
        "foreign access interface exists before preparation",
    )
    for lookup in (pwd.getpwnam, grp.getgrnam):
        try:
            lookup(ACCOUNT)
        except KeyError:
            pass
        else:
            raise Refusal("foreign forwarding identity exists before preparation")
    for identifier in run(["nmcli", "-g", "UUID", "connection", "show"]).stdout.splitlines():
        require(
            run(["nmcli", "-g", "connection.interface-name", "connection", "show", identifier]).stdout.strip()
            != INTERFACE,
            "foreign NetworkManager connection exists before preparation",
        )
    require(
        firewall(f"--get-zone-of-interface={intent['external_interface']}") == intent["external_zone"],
        "external interface zone differs before preparation",
    )
    require(
        firewall(f"--zone={intent['external_zone']}", "--query-service=ssh", permanent=True) == "yes",
        "permanent external-zone SSH service must already preserve administrator ingress",
    )
    firewall_policy_prerequisites()
    verify_units_owned(fresh=True, allow_missing_wireguard=True)
    missing = []
    for package in PACKAGES:
        result = run(["rpm", "-q", "--whatprovides", package], allow_failure=True)
        require(result.returncode in (0, 1), "package observation failed")
        if result.returncode == 1:
            missing.append(package)
    plan = {
        "changed": False,
        "state": "prerequisite_candidate",
        "missing_packages": missing,
        "reserve_unmanaged_interface": INTERFACE,
        "admit_selinux_tcp_port": 2222,
        "firewalld_zone": ZONE,
        "reloads": ["firewalld when creating zone", "NetworkManager configuration if active"],
        "requires": "review pending permanent configuration and retain tested provider console",
    }
    if action == "prepare-plan":
        return plan
    private_write(PREPARE_RECEIPT, json.dumps({"complete": False, "intent": intent}) + "\n")
    if missing:
        run(
            ["zypper", "--non-interactive", "--no-refresh", "install", "--no-recommends", "--", *missing],
            timeout=1800,
        )
    require(run(["getenforce"]).stdout.strip() == "Enforcing", "SELinux enforcement changed")
    ports = run(["semanage", "port", "-l"]).stdout
    require(not exact_port_conflict(ports), "TCP 2222 already belongs to another SELinux type")
    local_ports = run(["semanage", "port", "-l", "-C"]).stdout
    require(not exact_port_conflict(local_ports, include_ranges=True), "custom SELinux port range overlaps TCP 2222")
    local_contexts = run(["semanage", "fcontext", "-l", "-C"]).stdout
    context_additions = []
    for path, label in (
        (ROOT / "authorized_keys", "ssh_home_t"),
        (ROOT / "ssh_host_ed25519_key", "sshd_key_t"),
        (ROOT / "ssh_host_ed25519_key.pub", "sshd_key_t"),
    ):
        require(not custom_context_conflict(local_contexts, str(path), label), "conflicting custom SELinux path rule")
        context = run(["matchpathcon", "-n", str(path)]).stdout.strip().split(":")
        if len(context) < 3 or context[2] != label:
            context_additions.append((path, label))
    if not ssh_port_admitted(ports):
        run(["semanage", "port", "-a", "-t", "ssh_port_t", "-p", "tcp", "2222"])
    for path, label in context_additions:
        run(["semanage", "fcontext", "-a", "-t", label, re.escape(str(path))])
    require(
        NM_CONFIG.parent.is_dir() and not NM_CONFIG.parent.is_symlink(),
        "NetworkManager configuration directory missing/unsafe",
    )
    private_write(NM_CONFIG, NM_CONTENT)
    run(["restorecon", str(NM_CONFIG)])
    if run(["systemctl", "is-active", "NetworkManager.service"], allow_failure=True).returncode == 0:
        run(["nmcli", "general", "reload", "conf"])
    require(
        firewall(f"--zone={intent['external_zone']}", "--query-service=ssh", permanent=True) == "yes",
        "permanent external-zone SSH service must already preserve administrator ingress",
    )
    permanent = firewall("--get-zones", permanent=True).split()
    runtime = firewall("--get-zones").split()
    require((ZONE in permanent) == (ZONE in runtime), "partially prepared firewall zone")
    if ZONE not in permanent:
        firewall(f"--new-zone={ZONE}", permanent=True)
        firewall(f"--zone={ZONE}", "--set-target=DROP", permanent=True)
        firewall("--reload")
    prerequisites(intent, existing=False)
    PREPARE_RECEIPT.write_text(json.dumps({"complete": True, "intent": intent}) + "\n")
    return {**plan, "changed": True, "state": "prerequisites_prepared"}


if __name__ == "__main__":
    try:
        if sys.argv[1] in ("revoke", "revoke-plan"):
            result = revoke(json.load(sys.stdin), plan=sys.argv[1] == "revoke-plan")
        else:
            operation = prepare if sys.argv[1].startswith("prepare-") else operate
            result = operation(sys.argv[1], json.load(sys.stdin))
        print(json.dumps(result))
    except Refusal as error:
        sys.exit(f"Access refused: {error}. No automatic recovery attempted.")
    except (Refusal, OSError, ValueError, KeyError, subprocess.SubprocessError):
        # No command output, config text, exception repr, or private key crosses this boundary.
        sys.exit(
            "Access refused or incomplete; inspect host prerequisites/owned paths with the administrator. No automatic recovery attempted."
        )
