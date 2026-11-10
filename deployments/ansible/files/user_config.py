"""Shared personal-file publication and explicit ordinary-user shell selection.

Home writes require the selected account's own authority. Only the shell-login operation
changes an existing account, as root. Planning and verification never create files.
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
SHELL_MARKER = "# Managed by LychD interactive shell v1\n"
ZSH_HOOK = 'source "$HOME/.config/lychd-shell/zshrc"'
ZSH_FILES = frozenset({".zshrc", ".config/lychd-shell/zshrc"})
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


def managed_files(root, uid, files, mode, *, policy=False, marker=MARKER, preserve=None):
    """Plan or publish only safe managed leaves using no-follow directory descriptors."""
    if mode not in {"plan", "apply", "verify"}:
        raise Refusal("Unknown operation")
    preserve = preserve or {}
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
                if existing is not None and relative in preserve and not existing[0].startswith(marker):
                    if preserve[relative] not in existing[0].splitlines():
                        raise Refusal(f"Preserve foreign configuration; add the documented source hook: {relative}")
                    continue
                if existing is not None and existing[0] != content:
                    if policy or not existing[0].startswith(marker):
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
                        if policy or not existing[0].startswith(marker):
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


def shell_selection(intent):
    """Validate the selected ordinary identity before package, home or account effects."""
    shell = intent["shell"]
    if not isinstance(shell, str) or shell not in {"zsh", "fish"}:
        raise Refusal("Select exactly zsh or fish")
    if not isinstance(intent["set_login"], bool):
        raise Refusal("set_login must be a boolean")
    observed = account(intent["user"])
    entry = pwd.getpwnam(intent["user"])
    try:
        runtime_uid = pwd.getpwnam("lychd").pw_uid
    except KeyError:
        runtime_uid = None
    if (
        observed["uid"] < 1000
        or observed["name"] in {"root", "lychd", "lychd-view"}
        or observed["uid"] == runtime_uid
        or entry.pw_shell.rsplit("/", 1)[-1] in {"false", "nologin"}
    ):
        raise Refusal("Select an ordinary personal/administrator account, separate from the runtime UID")
    return observed, entry.pw_shell, "/usr/bin/" + shell


def shell_preflight(intent):
    observed, login, desired = shell_selection(intent)
    with open("/etc/os-release", encoding="utf-8") as stream:
        values = dict(line.rstrip().split("=", 1) for line in stream if "=" in line)
    if values.get("ID", "").strip('"') != "opensuse-tumbleweed":
        raise Refusal("Requires installed openSUSE Tumbleweed; no KDE is required")
    # Validate the home even for Fish, which needs no extra startup defaults.
    descriptor = open_root(observed["home"], observed["uid"])
    os.close(descriptor)
    return {
        "identity": observed,
        "login_shell": login,
        "login_change": intent["set_login"] and login != desired,
    }


def history_state(home, uid, mode):
    """Create a private new history without reading, replacing or truncating existing data."""
    root_fd = open_root(home, uid)
    fd = None
    try:
        fd = parent_directory(root_fd, [".local", "state", "lychd-shell"], uid, mode == "apply", 0o700)
        changed = fd is None
        if fd is not None:
            if stat.S_IMODE(os.fstat(fd).st_mode) != 0o700:
                raise Refusal("Zsh history directory must be private (0700); inspect it manually")
            try:
                descriptor = os.open("history", os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
            except FileNotFoundError:
                changed = True
                if mode == "apply":
                    descriptor = os.open(
                        "history", os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd
                    )
                else:
                    descriptor = None
            if descriptor is not None:
                try:
                    value = os.fstat(descriptor)
                    if (
                        not stat.S_ISREG(value.st_mode)
                        or value.st_uid != uid
                        or value.st_nlink != 1
                        or stat.S_IMODE(value.st_mode) != 0o600
                    ):
                        raise Refusal("Zsh history must be an owned singly linked private (0600) regular file")
                finally:
                    os.close(descriptor)
        if mode == "verify" and changed:
            raise Refusal("Missing private Zsh history")
        return [".local/state/lychd-shell/history"] if changed else []
    finally:
        if fd is not None:
            os.close(fd)
        os.close(root_fd)


def shell_files(mode, intent):
    observed, _, _ = shell_selection(intent)
    if observed != intent["identity"] or observed["uid"] != os.geteuid():
        raise Refusal("Shell files require the unchanged selected user's own authority")
    files = intent["files"]
    expected = ZSH_FILES if intent["shell"] == "zsh" else frozenset()
    if set(files) != expected or not all(value.startswith(SHELL_MARKER) for value in files.values()):
        raise Refusal("Only the selected shell's marked defaults are allowed")
    options = {"marker": SHELL_MARKER, "preserve": {".zshrc": ZSH_HOOK}}
    # Refuse every conflicting destination before any home mutation.
    if mode == "apply":
        managed_files(observed["home"], observed["uid"], files, "plan", **options)
        if intent["shell"] == "zsh":
            history_state(observed["home"], observed["uid"], "plan")
    result = managed_files(observed["home"], observed["uid"], files, mode, **options)
    if intent["shell"] == "zsh":
        result["changed"] += history_state(observed["home"], observed["uid"], mode)
    return result


def shell_login(mode, intent):
    """Observe selected shell usability, then change only the admitted existing account."""
    observed, login, desired = shell_selection(intent)
    if observed != intent["identity"] or os.geteuid() != 0:
        raise Refusal("Login shell requires administrator authority and unchanged selected identity")
    changed = intent["set_login"] and login != desired
    if mode in {"apply", "verify"}:
        if not os.path.isfile(desired) or not os.access(desired, os.X_OK):
            raise Refusal("Selected shell executable must be installed and executable")
        if intent["set_login"]:
            with open("/etc/shells", encoding="utf-8") as stream:
                allowed = {line.strip() for line in stream if not line.startswith("#")}
            if desired not in allowed:
                raise Refusal("Selected login shell must be listed in /etc/shells")
    if mode == "verify" and changed:
        raise Refusal("Selected login shell differs")
    if mode == "apply" and changed:
        subprocess.run(["/usr/sbin/usermod", "--shell", desired, observed["name"]], check=True, capture_output=True)
    return {"changed": changed, "operation": mode}


def execute(mode, intent):
    if mode == "preflight":
        return preflight(intent["user"])
    if mode == "shell-preflight":
        return shell_preflight(intent)
    if mode not in {"plan", "apply", "verify"}:
        raise Refusal("Unknown operation")
    if intent["kind"] == "shell":
        return shell_files(mode, intent)
    if intent["kind"] == "shell-login":
        return shell_login(mode, intent)
    kind = intent["kind"]
    if kind == "user":
        observed = account(intent["user"])
        if observed["uid"] != os.geteuid() or observed != intent["identity"]:
            raise Refusal("Personal files require the unchanged selected user's own authority")
        files = intent["files"]
        shell = intent["shell"]
        if not isinstance(shell, str) or shell not in {"zsh", "fish"}:
            raise Refusal("Select exactly zsh or fish")
        expected = USER_FILES if shell == "fish" else USER_FILES - {".config/fish/conf.d/60-lychd-workstation.fish"}
        if set(files) != expected or not all(value.startswith(MARKER) for value in files.values()):
            raise Refusal("Only the selected marked workstation files are allowed")
        return managed_files(observed["home"], observed["uid"], files, mode)
    if kind == "policy" and os.geteuid() == 0:
        content = json.dumps(POLICY, indent=2) + "\n"
        return managed_files("/etc", 0, {"firefox/policies/policies.json": content}, mode, policy=True)
    raise Refusal("Unknown kind or missing policy administrator authority")


if __name__ == "__main__":
    try:
        print(json.dumps(execute(sys.argv[1], json.load(sys.stdin))))
    except (Refusal, OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"User configuration refusal: {error}", file=sys.stderr)
        sys.exit(1)
