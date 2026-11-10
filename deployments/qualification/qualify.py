#!/usr/bin/env python3
"""One real, owned QEMU snapshot upgrade; offline checks never qualify a VM."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import resource
import shlex
import shutil
import signal
import stat
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
MAX_OVERLAY = 24 * 1024**3
MAX_LOG = 32 * 1024**2
TOTAL_SECONDS = 3600


class Refusal(ValueError):
    """An input or observed result does not satisfy the admitted contract."""


def require(value, message):
    if not value:
        raise Refusal(message)


def closed(value, fields):
    require(isinstance(value, dict) and set(value) == set(fields.split()), "unknown or missing fields")


def hex_value(value, length):
    require(isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value), "invalid hexadecimal pin")


def identifier(value):
    require(isinstance(value, str), "canonical UUID required")
    try:
        require(str(uuid.UUID(value)) == value, "canonical UUID required")
    except ValueError:
        raise Refusal("canonical UUID required") from None


def load_json(path):
    def unique(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate JSON key refused")
            result[key] = value
        return result

    return json.loads(path.read_text(), object_pairs_hook=unique)


def ssh_literal(value):
    require(not any(ord(character) < 32 for character in value), "control character in SSH path")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'


def variables(path, allowed):
    value = load_json(path)
    require(isinstance(value, dict) and set(value) <= set(allowed.split()), "unknown Ansible variable refused")

    def inert(item):
        if isinstance(item, str):
            require(not any(token in item for token in ("{{", "{%", "{#")), "templated variable refused")
        elif isinstance(item, dict):
            for entry in item.values():
                inert(entry)
        elif isinstance(item, list):
            for entry in item:
                inert(entry)

    inert(value)
    return value


def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def trusted_file(value, private=False):
    require(isinstance(value, str) and Path(value).is_absolute(), "absolute file path required")
    path = Path(value)
    require(path.resolve(strict=True) == path, "symlinked file path refused")
    info = path.stat()
    require(stat.S_ISREG(info.st_mode) and info.st_nlink == 1, "single-link regular file required")
    require(info.st_uid in {0, os.getuid()} and not info.st_mode & 0o022, "untrusted file ownership or mode")
    if private:
        require(info.st_uid == os.getuid() and not info.st_mode & 0o077, "private operator-owned file required")
        require(not path.is_relative_to(ROOT), "private inputs belong outside the checkout")
    return path


def admitted_file(value, private=False):
    closed(value, "path sha256")
    hex_value(value["sha256"], 64)
    path = trusted_file(value["path"], private)
    require(digest(path) == value["sha256"], "file hash mismatch")
    return path


def source_digest():
    result = hashlib.sha256()
    for directory in (ROOT / "deployments/ansible", ROOT / "deployments/qualification"):
        for path in sorted(directory.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                require(not path.is_symlink(), "symlinked controller source refused")
                result.update(str(path.relative_to(ROOT)).encode() + b"\0")
                result.update(bytes.fromhex(digest(path)))
    return result.hexdigest()


def repositories(values, snapshot):
    require(isinstance(values, list) and 1 <= len(values) <= 2, "one or two explicit repositories required")
    seen = set()
    for repo in values:
        closed(repo, "name url repomd_sha256 key fingerprint")
        require(repo["name"] in {"oss", "non-oss"} and repo["name"] not in seen, "repository name refused")
        seen.add(repo["name"])
        require(
            repo["url"] == f"https://download.opensuse.org/history/{snapshot}/tumbleweed/repo/{repo['name']}/",
            "exact official snapshot repository required",
        )
        hex_value(repo["repomd_sha256"], 64)
        require(re.fullmatch(r"[0-9A-F]{40}", repo["fingerprint"] or ""), "explicit signing fingerprint required")
        admitted_file(repo["key"])
    require("oss" in seen, "OSS repository required")


def validate_plan(plan):
    closed(plan, "schema run_id controller_source_sha256 baseline candidate application ssh inputs access")
    require(type(plan["schema"]) is int and plan["schema"] == 1, "unsupported plan schema")
    identifier(plan["run_id"])
    hex_value(plan["controller_source_sha256"], 64)
    require(plan["controller_source_sha256"] == source_digest(), "controller source digest mismatch")
    baseline, candidate = plan["baseline"], plan["candidate"]
    closed(baseline, "snapshot baseline_id machine_id image provenance repositories")
    closed(candidate, "snapshot repositories")
    for value in (baseline["snapshot"], candidate["snapshot"]):
        require(isinstance(value, str) and re.fullmatch(r"20[0-9]{6}", value), "explicit dated snapshot required")
        time.strptime(value, "%Y%m%d")
    require(candidate["snapshot"] > baseline["snapshot"], "candidate must be later than baseline")
    identifier(baseline["baseline_id"])
    hex_value(baseline["machine_id"], 32)
    admitted_file(baseline["image"], private=True)
    provenance = baseline["provenance"]
    closed(provenance, "url image_sha256 checksum signature keyring signer_fingerprint")
    url = urlparse(provenance["url"])
    require(
        url.scheme == "https"
        and url.netloc == "download.opensuse.org"
        and url.path.startswith("/tumbleweed/appliances/")
        and url.path.endswith(".qcow2")
        and not url.query
        and not url.fragment,
        "official upstream qcow2 provenance URL required",
    )
    hex_value(provenance["image_sha256"], 64)
    require(re.fullmatch(r"[0-9A-F]{40}", provenance["signer_fingerprint"] or ""), "image signer pin required")
    for name in ("checksum", "signature", "keyring"):
        admitted_file(provenance[name])
    for snapshot in (baseline, candidate):
        repositories(snapshot["repositories"], snapshot["snapshot"])
    closed(plan["application"], "revision image_id")
    hex_value(plan["application"]["revision"], 40)
    hex_value(plan["application"]["image_id"], 64)
    ssh = plan["ssh"]
    closed(ssh, "port host_key admin_key runtime_key")
    require(type(ssh["port"]) is int and 1024 <= ssh["port"] <= 65535, "unprivileged localhost SSH port required")
    require(
        isinstance(ssh["host_key"], str) and re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/]+={0,2}", ssh["host_key"]),
        "one pinned Ed25519 SSH host key required",
    )
    for name in ("admin_key", "runtime_key"):
        admitted_file(ssh[name], private=True)
    closed(plan["inputs"], "host_vars source_vars image_vars")
    for value in plan["inputs"].values():
        admitted_file(value, private=True)
    source = variables(
        Path(plan["inputs"]["source_vars"]["path"]),
        "lychd_source_revision lychd_source_uv_local_binary lychd_source_uv_sha256 lychd_source_python",
    )
    image = variables(
        Path(plan["inputs"]["image_vars"]["path"]),
        "lychd_image_archive lychd_image_archive_sha256 lychd_image_id lychd_image_ref lychd_image_revision lychd_image_staging_dir",
    )
    variables(
        Path(plan["inputs"]["host_vars"]["path"]),
        "lychd_runtime_name lychd_runtime_uid lychd_runtime_gid lychd_subuid_start lychd_subgid_start lychd_subid_count lychd_runtime_ssh_public_keys lychd_floor_enable_network_online",
    )
    require(source.get("lychd_source_revision") == plan["application"]["revision"], "source revision mismatch")
    require(image.get("lychd_image_id") == plan["application"]["image_id"], "image ID mismatch")
    require(image.get("lychd_image_revision") == plan["application"]["revision"], "image revision mismatch")
    require(
        image.get("lychd_image_ref") == "localhost/lychd:" + plan["application"]["revision"], "image reference mismatch"
    )
    if plan["access"] is not None:
        closed(plan["access"], "profile variables")
        require(plan["access"]["profile"] == "host-access-v1", "unknown access qualification profile")
        admitted_file(plan["access"]["variables"], private=True)
        access = variables(
            Path(plan["access"]["variables"]["path"]),
            "lychd_access_enabled lychd_access_prepare lychd_access_prepare_target lychd_access_target lychd_access_intent",
        )
        require(
            access.get("lychd_access_enabled") is True and access.get("lychd_access_prepare", False) is False,
            "access observation must be enabled without preparation",
        )
    return plan


def process_identity(pid):
    """Bind PID reuse protection to the actual Linux executable and start time."""
    proc = Path("/proc") / str(pid)
    return (str((proc / "exe").resolve(strict=True)), (proc / "stat").read_text().rsplit(")", 1)[1].split()[19])


def terminate_owned(process, identity):
    """Stop only this invocation's still-identical QEMU, with a bounded grace period."""
    if process.poll() is not None:
        return
    require(process_identity(process.pid) == identity, "QEMU ownership changed; refusing signal")
    process.terminate()
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        require(process_identity(process.pid) == identity, "QEMU ownership changed before kill")
        process.kill()
        process.wait(timeout=10)


class Qualification:
    def __init__(self, plan, work, controller):
        self.plan, self.work, self.controller = plan, work, controller
        self.deadline = time.monotonic() + TOTAL_SECONDS
        self.process = None
        self.identity = None
        self.output_thread = None
        self.output_overflow = False
        self.sequence = 0
        self.receipt = {
            "schema": "lychd.tumbleweed-qualification",
            "version": 1,
            "run_id": plan["run_id"],
            "status": "running",
            "controller_source_sha256": plan["controller_source_sha256"],
            "baseline_snapshot": plan["baseline"]["snapshot"],
            "candidate_snapshot": plan["candidate"]["snapshot"],
            "baseline_image_sha256": plan["baseline"]["image"]["sha256"],
            "ssh_host_key_sha256": hashlib.sha256(plan["ssh"]["host_key"].encode()).hexdigest(),
            "inputs_sha256": {key: value["sha256"] for key, value in plan["inputs"].items()},
            "upstream_image": {
                key: plan["baseline"]["provenance"][key] for key in ("url", "image_sha256", "signer_fingerprint")
            },
            "repository_pins": {
                phase: [
                    {
                        "name": repo["name"],
                        "url": repo["url"],
                        "repomd_sha256": repo["repomd_sha256"],
                        "signer_fingerprint": repo["fingerprint"],
                        "key_sha256": repo["key"]["sha256"],
                    }
                    for repo in plan[phase]["repositories"]
                ]
                for phase in ("baseline", "candidate")
            },
            "application": plan["application"],
            "access_profile": None if plan["access"] is None else plan["access"]["profile"],
            "stages": [],
        }

    def save(self):
        target = self.work / "receipt.json"
        temporary = self.work / "receipt.new"
        temporary.write_text(json.dumps(self.receipt, indent=2, sort_keys=True) + "\n")
        temporary.chmod(0o600)
        temporary.replace(target)

    def command(self, stage, argv, *, stdin=None, timeout=300, allow_disconnect=False):
        require(not self.output_overflow, "QEMU serial output exceeded its ceiling")
        self.sequence += 1
        record = {"name": stage, "ok": False}
        self.receipt["stages"].append(record)
        self.save()
        remaining = self.deadline - time.monotonic()
        require(remaining > 0, "total qualification deadline exceeded")
        log = self.work / f"{self.sequence:02d}-{stage}.log"
        env = {
            "PATH": str(self.controller / "bin") + ":/usr/bin:/bin",
            "HOME": str(self.work),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "ANSIBLE_HOME": str(self.work / "ansible"),
            "ANSIBLE_CONFIG": str(ROOT / "deployments/ansible/ansible.cfg"),
            "ANSIBLE_STDOUT_CALLBACK": "default",
            "ANSIBLE_CALLBACKS_ENABLED": "",
            "ANSIBLE_NOCOLOR": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        try:
            with log.open("wb") as stream:

                def limits():
                    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_LOG, MAX_LOG))

                child = subprocess.Popen(
                    argv,
                    stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    env=env,
                    start_new_session=True,
                    preexec_fn=limits,
                    cwd=ROOT / "deployments/ansible",
                )
                try:
                    child.communicate(stdin.encode() if stdin is not None else None, timeout=min(timeout, remaining))
                except BaseException:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait(timeout=10)
                    raise
            record["exit_code"] = child.returncode
            require(child.returncode == 0 or allow_disconnect and child.returncode == 255, "stage failed")
            require(log.stat().st_size < MAX_LOG, "stage output reached its ceiling")
            record["ok"] = True
            return log.read_text(errors="replace")
        finally:
            if log.exists():
                record["log_sha256"] = digest(log)
            self.save()

    def ssh(self, user, action, payload, stage, **options):
        code = (ROOT / "deployments/qualification/guest.py").read_text()
        remote = shlex.join(["/usr/bin/python3", "-c", code, action])
        return self.command(
            stage,
            [self.tools["ssh"], "-F", str(self.work / "ssh_config"), "-l", user, "qualification", remote],
            stdin=json.dumps(payload),
            **options,
        )

    def wait_ssh(self, phase):
        end = min(time.monotonic() + 300, self.deadline)
        attempts = 0
        while time.monotonic() < end:
            attempts += 1
            require(self.process.poll() is None, "owned QEMU exited before SSH readiness")
            require(not self.output_overflow, "QEMU serial output exceeded its ceiling")
            try:
                checked = subprocess.run(
                    [
                        self.tools["ssh"],
                        "-F",
                        str(self.work / "ssh_config"),
                        "qualification",
                        "/usr/bin/cat /proc/sys/kernel/random/boot_id",
                    ],
                    stdin=subprocess.DEVNULL,
                    capture_output=True,
                    text=True,
                    timeout=min(15, max(0.1, end - time.monotonic())),
                    check=False,
                )
            except subprocess.TimeoutExpired:
                continue
            boot_id = checked.stdout.strip()
            if checked.returncode == 0 and (phase == "baseline" or boot_id != self.receipt["baseline_boot_id"]):
                self.receipt["stages"].append(
                    {"name": phase + "-ssh-ready", "ok": True, "readiness_attempts": attempts}
                )
                self.save()
                return
            time.sleep(2)
        raise Refusal("SSH readiness deadline exceeded")

    def prepare(self):
        self.tools = {}
        for name in ("qemu-img", "qemu-system-x86_64", "ssh", "ssh-keygen", "gpg", "gpgv"):
            tool = shutil.which(name)
            require(tool is not None, "required controller tool unavailable")
            self.tools[name] = str(trusted_file(str(Path(tool).resolve())))
        ansible = trusted_file(str((self.controller / "bin/ansible-playbook").resolve()))
        self.ansible = str(ansible)
        provenance = self.plan["baseline"]["provenance"]
        output = self.command(
            "image-signature",
            [
                self.tools["gpgv"],
                "--status-fd",
                "1",
                "--keyring",
                provenance["keyring"]["path"],
                provenance["signature"]["path"],
                provenance["checksum"]["path"],
            ],
        )
        valid = []
        for line in output.splitlines():
            if line.startswith("[GNUPG:] VALIDSIG "):
                fields = line.split()
                valid.append(fields[-1] if len(fields) >= 12 else fields[2])
        require(valid == [provenance["signer_fingerprint"]], "image checksum signer mismatch")
        checksums = Path(provenance["checksum"]["path"]).read_text().splitlines()
        name = Path(urlparse(provenance["url"]).path).name
        require(
            any(
                line.split() == [provenance["image_sha256"], name]
                or line.split() == [provenance["image_sha256"], "*" + name]
                for line in checksums
            ),
            "signed upstream image checksum mismatch",
        )
        for phase in ("baseline", "candidate"):
            for repo in self.plan[phase]["repositories"]:
                output = self.command(
                    phase + "-" + repo["name"] + "-key",
                    [
                        self.tools["gpg"],
                        "--batch",
                        "--no-options",
                        "--homedir",
                        str(self.work / "gnupg"),
                        "--with-colons",
                        "--show-keys",
                        repo["key"]["path"],
                    ],
                )
                primary = output.split("pub:", 1)[-1].split("sub:", 1)[0]
                require(
                    len(re.findall(r"^pub:", output, re.M)) == 1
                    and re.findall(r"^fpr:::::::::([0-9A-F]{40}):", primary, re.M) == [repo["fingerprint"]],
                    "repository signer mismatch",
                )
        key = self.work / "known_hosts"
        key.write_text(f"[127.0.0.1]:{self.plan['ssh']['port']} {self.plan['ssh']['host_key']}\n")
        config = (
            "Host qualification 127.0.0.1\n"
            "  HostName 127.0.0.1\n"
            f"  Port {self.plan['ssh']['port']}\n  User root\n"
            f"  UserKnownHostsFile {ssh_literal(str(key))}\n  GlobalKnownHostsFile /dev/null\n"
            "  StrictHostKeyChecking yes\n  CheckHostIP yes\n  UpdateHostKeys no\n"
            "  IdentitiesOnly yes\n  BatchMode yes\n  PasswordAuthentication no\n"
            "  KbdInteractiveAuthentication no\n  ConnectTimeout 5\n  ConnectionAttempts 1\n"
            "  ServerAliveInterval 10\n  ServerAliveCountMax 2\n"
        )
        for user, field in (("root", "admin_key"), ("lychd", "runtime_key")):
            config += (
                f"Match host 127.0.0.1 user {user}\n  IdentityFile {ssh_literal(self.plan['ssh'][field]['path'])}\n"
            )
        (self.work / "ssh_config").write_text(config)
        (self.work / "inventory.json").write_text(
            json.dumps(
                {
                    "all": {
                        "children": {
                            "lychd_hosts": {
                                "hosts": {
                                    "pilot": {
                                        "ansible_host": "127.0.0.1",
                                        "ansible_port": self.plan["ssh"]["port"],
                                        "ansible_user": "root",
                                    }
                                }
                            }
                        }
                    }
                }
            )
        )
        for path in (key, self.work / "ssh_config", self.work / "inventory.json"):
            path.chmod(0o600)
        self.command("ssh-host-key", [self.tools["ssh-keygen"], "-lf", str(key)])

    def launch(self):
        image = self.plan["baseline"]["image"]["path"]
        info = json.loads(self.command("baseline-image-info", [self.tools["qemu-img"], "info", "--output=json", image]))
        require(info["format"] == "qcow2" and not info.get("backing-filename"), "standalone qcow2 required")
        require(0 < info["virtual-size"] <= 64 * 1024**3, "baseline virtual disk exceeds ceiling")
        require(shutil.disk_usage(self.work).free >= MAX_OVERLAY + 1024**3, "insufficient overlay reserve")
        overlay = self.work / "overlay.qcow2"
        self.command(
            "overlay-create",
            [self.tools["qemu-img"], "create", "-f", "qcow2", "-F", "qcow2", "-b", image, str(overlay)],
        )
        argv = [
            self.tools["qemu-system-x86_64"],
            "-no-user-config",
            "-nodefaults",
            "-machine",
            "q35,accel=tcg",
            "-cpu",
            "max",
            "-smp",
            "2",
            "-m",
            "3072",
            "-uuid",
            self.plan["run_id"],
            "-display",
            "none",
            "-monitor",
            "none",
            "-serial",
            "stdio",
            "-drive",
            f"file={overlay},if=none,id=os,format=qcow2",
            "-device",
            "virtio-blk-pci,drive=os",
            "-netdev",
            f"user,id=net0,hostfwd=tcp:127.0.0.1:{self.plan['ssh']['port']}-:22",
            "-device",
            "virtio-net-pci,netdev=net0",
        ]

        def limits():
            resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OVERLAY, MAX_OVERLAY))

        self.process = subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            start_new_session=True,
            preexec_fn=limits,
        )
        self.output_thread = threading.Thread(target=self.capture_serial, daemon=True)
        self.output_thread.start()
        try:
            self.identity = process_identity(self.process.pid)
        except (FileNotFoundError, ProcessLookupError):
            self.process.wait(timeout=10)
            raise Refusal("QEMU failed to launch") from None
        require(self.identity[0] == self.tools["qemu-system-x86_64"], "QEMU executable mismatch")
        (self.work / "owned-process.json").write_text(
            json.dumps(
                {
                    "pid": self.process.pid,
                    "executable": self.identity[0],
                    "start_time": self.identity[1],
                    "run_id": self.plan["run_id"],
                }
            )
            + "\n"
        )

    def capture_serial(self):
        """Drain owned QEMU output while bounding persistent diagnostic bytes."""
        try:
            written = 0
            with (self.work / "serial.log").open("wb") as log:
                while block := self.process.stdout.read1(65536):
                    remaining = max(0, MAX_LOG - written)
                    log.write(block[:remaining])
                    written += len(block)
                    if written > MAX_LOG:
                        self.output_overflow = True
        except (OSError, ValueError):
            self.output_overflow = True

    def guest_payload(self, phase):
        return {
            "run_id": self.plan["run_id"],
            "baseline_id": self.plan["baseline"]["baseline_id"],
            "machine_id": self.plan["baseline"]["machine_id"],
            "snapshot": self.plan[phase]["snapshot"],
        }

    def observe(self, phase):
        observation = json.loads(self.ssh("root", "observe", self.guest_payload(phase), phase + "-identity"))
        self.receipt[phase + "_boot_id"] = observation["boot_id"]
        self.receipt[phase + "_packages"] = observation["packages"]
        self.save()
        self.ssh("lychd", "runtime", {}, phase + "-runtime")
        for playbook in ("verify", "app-verify", "server"):
            argv = [
                self.ansible,
                "-i",
                str(self.work / "inventory.json"),
                f"playbooks/{playbook}.yml",
                "--limit",
                "pilot",
                "--ssh-common-args",
                "-F " + shlex.quote(str(self.work / "ssh_config")),
            ]
            for value in self.plan["inputs"].values():
                argv.extend(["-e", "@" + value["path"]])
            output = self.command(phase + "-" + playbook, argv, timeout=600)
            changes = re.findall(r"\bchanged=(\d+)", output)
            require(changes and all(value == "0" for value in changes), "verification/idempotence reported changes")
            if playbook == "server":
                require("mode=verify" in output, "server observation did not select read-only verification")
        if self.plan["access"] is not None:
            argv = [
                self.ansible,
                "-i",
                str(self.work / "inventory.json"),
                "playbooks/access-verify.yml",
                "--limit",
                "pilot",
                "--ssh-common-args",
                "-F " + shlex.quote(str(self.work / "ssh_config")),
                "-e",
                "@" + self.plan["access"]["variables"]["path"],
                "-e",
                "lychd_access_target=pilot",
            ]
            output = self.command(phase + "-access", argv, timeout=300)
            changes = re.findall(r"\bchanged=(\d+)", output)
            require(changes and all(value == "0" for value in changes), "access verifier reported changes")

    def run(self):
        self.prepare()
        self.launch()
        self.wait_ssh("baseline")
        self.observe("baseline")
        payload = self.guest_payload("baseline")
        payload["repositories"] = self.plan["baseline"]["repositories"]
        self.ssh("root", "metadata", payload, "baseline-metadata")
        payload = self.guest_payload("baseline")
        payload["candidate_snapshot"] = self.plan["candidate"]["snapshot"]
        payload["repositories"] = self.plan["candidate"]["repositories"]
        for repo in payload["repositories"]:
            repo["key_data"] = base64.b64encode(Path(repo["key"]["path"]).read_bytes()).decode()
        self.ssh("root", "upgrade", payload, "snapshot-upgrade", timeout=1800)
        self.ssh("root", "reboot", self.guest_payload("candidate"), "controlled-reboot", allow_disconnect=True)
        # Require actual disconnection/boot-ID transition; do not reuse a pre-reboot session.
        time.sleep(3)
        self.wait_ssh("candidate")
        self.observe("candidate")
        require(self.receipt["candidate_boot_id"] != self.receipt["baseline_boot_id"], "reboot did not change boot ID")
        self.ssh("root", "shutdown", self.guest_payload("candidate"), "controlled-shutdown", allow_disconnect=True)
        self.process.wait(timeout=min(30, max(0.1, self.deadline - time.monotonic())))
        require(self.process.returncode == 0, "guest did not shut down cleanly")
        required = {
            "image-signature",
            "baseline-image-info",
            "overlay-create",
            "baseline-metadata",
            "snapshot-upgrade",
            "controlled-reboot",
            "controlled-shutdown",
        }
        for phase in ("baseline", "candidate"):
            required.update(
                phase + "-" + name for name in ("ssh-ready", "identity", "runtime", "verify", "app-verify", "server")
            )
            if self.plan["access"] is not None:
                required.add(phase + "-access")
        observed = {stage["name"] for stage in self.receipt["stages"] if stage["ok"]}
        require(
            required <= observed and all(stage["ok"] for stage in self.receipt["stages"]),
            "required qualification stage missing or failed",
        )
        require(not self.output_overflow, "QEMU serial output exceeded its ceiling")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-digest", action="store_true")
    parser.add_argument("--plan")
    parser.add_argument("--work-dir")
    parser.add_argument("--controller")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--authorize-upgrade")
    args = parser.parse_args()
    if args.source_digest:
        print(source_digest())
        return 0
    qualification = None

    def cancelled(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, cancelled)
    try:
        os.umask(0o077)
        plan = validate_plan(load_json(trusted_file(args.plan, private=True)))
        require(args.work_dir and Path(args.work_dir).is_absolute(), "absolute work directory required")
        work = Path(args.work_dir)
        require(
            "," not in str(work) and not any(ord(character) < 32 for character in str(work)),
            "QEMU work directory contains reserved characters",
        )
        require(
            not work.exists() and work.parent.resolve(strict=True) == work.parent,
            "new nonsymlinked work directory required",
        )
        require(args.controller and Path(args.controller).is_absolute(), "absolute controller required")
        controller = Path(args.controller)
        trusted_file(str((controller / "bin/ansible-playbook").resolve(strict=True)))
        if args.check:
            print("Plan validated offline; no VM qualification performed.")
            return 0
        require(os.geteuid() != 0, "real qualification requires an unprivileged controller identity")
        token = f"{plan['run_id']}:{plan['baseline']['snapshot']}:{plan['candidate']['snapshot']}"
        require(args.authorize_upgrade == token, "exact explicit upgrade authorization required")
        work.mkdir(mode=0o700)
        (work / "gnupg").mkdir(mode=0o700)
        qualification = Qualification(plan, work, controller)
        qualification.save()
        try:
            qualification.run()
        finally:
            if qualification.process is not None and qualification.identity is not None:
                terminate_owned(qualification.process, qualification.identity)
            if qualification.output_thread is not None:
                qualification.output_thread.join(timeout=5)
                require(not qualification.output_thread.is_alive(), "QEMU output capture did not settle")
        require(not qualification.output_overflow, "QEMU output capture failed")
        qualification.receipt["status"] = "passed"
        qualification.save()
        print("Disposable snapshot qualification passed; review the private receipt.")
        return 0
    except (
        Refusal,
        OSError,
        ValueError,
        KeyError,
        TypeError,
        AttributeError,
        subprocess.SubprocessError,
        KeyboardInterrupt,
    ) as error:
        if qualification is not None:
            qualification.receipt["status"] = "failed"
            qualification.receipt["failure"] = type(error).__name__
            (qualification.work / "failure.private.txt").write_text(str(error) + "\n")
            qualification.save()
        print("Qualification refused or failed; retained private evidence is not a passing receipt.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
