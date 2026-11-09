"""Bounded workstation observation and managed-file publication, without account mutation.

Personal operations must run as the selected existing account. Root is used only for
platform observation and the optional fixed Firefox policy. Check/verify never mkdir.
"""

import contextlib
import json
import os
import pwd
import re
import stat
import subprocess
import sys
import uuid

MARKER = "# Managed by LychD workstation baseline v1\n"
USER_FILES = frozenset(
    {
        ".config/fish/conf.d/60-lychd-workstation.fish",
        ".config/lychd-workstation-starship.toml",
        ".local/share/konsole/LychD-Workstation.profile",
    }
)
POLICY = {
    "policies": {
        "ExtensionSettings": {
            "addon@darkreader.org": {
                "installation_mode": "normal_installed",
                "install_url": "https://addons.mozilla.org/firefox/downloads/latest/addon@darkreader.org/latest.xpi",
            }
        }
    }
}
DIRECTORY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


class Refusal(ValueError):
    """An observed boundary is unsafe or differs from explicit intent."""


def account(name):
    if not isinstance(name, str) or not re.fullmatch(r"[a-z_][a-z0-9_-]*[$]?", name):
        raise Refusal("Supply an explicit existing personal user name")
    try:
        entry = pwd.getpwnam(name)
    except KeyError as exc:
        raise Refusal("Personal user does not exist; this playbook never creates users") from exc
    if entry.pw_uid == 0 or not os.path.isabs(entry.pw_dir) or entry.pw_dir == "/":
        raise Refusal("Personal user must be non-root with an absolute existing home")
    return {
        "name": name,
        "uid": entry.pw_uid,
        "gid": entry.pw_gid,
        "home": entry.pw_dir,
    }


def preflight(name):
    values = {}
    with open("/etc/os-release", encoding="utf-8") as stream:
        for line in stream:
            if "=" in line:
                key, value = line.rstrip().split("=", 1)
                values[key] = value.strip('"')
    if values.get("ID") != "opensuse-tumbleweed":
        raise Refusal("Requires an installed openSUSE Tumbleweed workstation")
    result = subprocess.run(
        ["/usr/bin/rpm", "-q", "plasma6-workspace"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise Refusal("Requires existing KDE Plasma 6 (plasma6-workspace)")
    return {
        **account(name),
        "snapshot": values.get("VERSION_ID"),
        "kde": result.stdout.strip(),
    }


def safe_directory(fd, uid, *, ancestor=False):
    observed = os.fstat(fd)
    owners = {0, uid} if ancestor else {uid}
    sticky_root = ancestor and observed.st_uid == 0 and observed.st_mode & stat.S_ISVTX
    if observed.st_uid not in owners or (observed.st_mode & 0o022 and not sticky_root):
        raise Refusal("Directory has foreign ownership or unsafe group/other write access")


def open_root(path, uid):
    if not os.path.isabs(path) or ".." in path.split("/"):
        raise Refusal("Root must be an absolute normalized path")
    fd = os.open("/", DIRECTORY_FLAGS)
    try:
        safe_directory(fd, uid, ancestor=True)
        for component in filter(None, path.split("/")):
            child = os.open(component, DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
            safe_directory(fd, uid, ancestor=True)
        safe_directory(fd, uid)
        return fd
    except BaseException:
        os.close(fd)
        raise


def parent_directory(root_fd, components, uid, apply, mode):
    fd = os.dup(root_fd)
    try:
        for component in components:
            try:
                child = os.open(component, DIRECTORY_FLAGS, dir_fd=fd)
            except FileNotFoundError:
                if not apply:
                    os.close(fd)
                    return None
                os.mkdir(component, mode, dir_fd=fd)
                child = os.open(component, DIRECTORY_FLAGS, dir_fd=fd)
            os.close(fd)
            fd = child
            safe_directory(fd, uid)
        return fd
    except BaseException:
        os.close(fd)
        raise


def existing_file(fd, name, uid):
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
    except FileNotFoundError:
        return None
    with os.fdopen(descriptor, "rb") as stream:
        observed = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(observed.st_mode)
            or observed.st_uid != uid
            or observed.st_nlink != 1
            or observed.st_mode & 0o022
            or observed.st_size > 65536
        ):
            raise Refusal("Managed destination must be a safe, singly linked owned regular file")
        return stream.read().decode("utf-8"), stat.S_IMODE(observed.st_mode)


def managed_files(root, uid, files, mode, *, policy=False):
    """Plan or publish only safe managed leaves using no-follow directory descriptors."""
    if mode not in {"plan", "apply", "verify"}:
        raise Refusal("Unknown operation")
    apply = mode == "apply"
    file_mode, directory_mode = (0o644, 0o755) if policy else (0o600, 0o700)
    changed = []
    root_fd = open_root(root, uid)
    try:
        # Validate every destination before creating any directory or publishing any file.
        for relative, content in files.items():
            parts = relative.split("/")
            if any(part in {"", ".", ".."} for part in parts):
                raise Refusal("Unsafe managed relative name")
            fd = parent_directory(root_fd, parts[:-1], uid, False, directory_mode)
            if fd is None:
                changed.append(relative)
                continue
            try:
                existing = existing_file(fd, parts[-1], uid)
                if existing is not None and existing[0] != content:
                    if policy or not existing[0].startswith(MARKER):
                        raise Refusal(f"Preserve foreign configuration: {relative}")
                if policy and existing is not None and existing[1] != file_mode:
                    raise Refusal("Existing policy mode differs; inspect it before adoption")
                if existing != (content, file_mode):
                    changed.append(relative)
            finally:
                os.close(fd)
        if mode == "verify" and changed:
            raise Refusal("Missing or drifted managed files: " + ", ".join(changed))
        if apply:
            for relative in changed:
                parts = relative.split("/")
                fd = parent_directory(root_fd, parts[:-1], uid, True, directory_mode)
                temporary = ".lychd-workstation-" + uuid.uuid4().hex
                try:
                    existing = existing_file(fd, parts[-1], uid)
                    content = files[relative]
                    if existing is not None and existing[0] != content:
                        if policy or not existing[0].startswith(MARKER):
                            raise Refusal(f"Destination changed; preserve {relative}")
                    descriptor = os.open(
                        temporary,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        file_mode,
                        dir_fd=fd,
                    )
                    with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fchmod(stream.fileno(), file_mode)
                        os.fsync(stream.fileno())
                    if existing is None:
                        # Publish without replacing a concurrent creator.
                        os.link(
                            temporary,
                            parts[-1],
                            src_dir_fd=fd,
                            dst_dir_fd=fd,
                            follow_symlinks=False,
                        )
                    elif policy:
                        # Identical existing policies need no content replacement.
                        raise Refusal("Existing policy mode differs; inspect it before adoption")
                    else:
                        os.replace(temporary, parts[-1], src_dir_fd=fd, dst_dir_fd=fd)
                    os.fsync(fd)
                finally:
                    with contextlib.suppress(FileNotFoundError):
                        os.unlink(temporary, dir_fd=fd)
                    os.close(fd)
    finally:
        os.close(root_fd)
    return {"changed": changed, "operation": mode}


def execute(mode, intent):
    if mode == "preflight":
        return preflight(intent["user"])
    kind = intent["kind"]
    if kind == "user":
        observed = account(intent["user"])
        if observed["uid"] != os.geteuid() or observed != intent["identity"]:
            raise Refusal("Personal files require the unchanged selected user's own authority")
        files = intent["files"]
        if set(files) != USER_FILES or not all(value.startswith(MARKER) for value in files.values()):
            raise Refusal("Only the three marked workstation files are allowed")
        return managed_files(observed["home"], observed["uid"], files, mode)
    if kind == "policy" and os.geteuid() == 0:
        content = json.dumps(POLICY, indent=2) + "\n"
        return managed_files("/etc", 0, {"firefox/policies/policies.json": content}, mode, policy=True)
    raise Refusal("Unknown kind or missing policy administrator authority")


if __name__ == "__main__":
    try:
        print(json.dumps(execute(sys.argv[1], json.load(sys.stdin))))
    except (Refusal, OSError, ValueError, KeyError) as error:
        print(f"Workstation refusal: {error}", file=sys.stderr)
        sys.exit(1)
