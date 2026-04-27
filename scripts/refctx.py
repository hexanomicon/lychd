# ruff: noqa: T201, C901, INP001, PLR0911, PLR0912
"""refctx: a tiny CTX-inspired reference loader for agents.

This script is intentionally stdlib-only. It is designed for agent use inside
the LychD repository to inspect external reference repos staged under
``~/Documents/References``.

Workflow: list -> find -> tree/llm -> spy -> extract.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ROOT = Path.home() / "Documents" / "References"
DEFAULT_DEPTH = 3
DEFAULT_MAX_BYTES = 1_048_576
DEFAULT_MAX_LINES = 2_000
DEFAULT_PRINT_LIMIT = 40

ALLOWED_EXTENSIONS = {
    ".txt",
    ".md",
    ".rst",
    ".adoc",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".sh",
    ".fish",
    ".bash",
    ".zsh",
    ".go",
    ".rs",
    ".c",
    ".h",
    ".cpp",
    ".hpp",
    ".java",
    ".kt",
    ".rb",
    ".php",
    ".css",
    ".scss",
    ".html",
    ".htm",
    ".sql",
    ".dockerfile",
}

SPECIAL_FILENAMES = {
    "readme",
    "readme.md",
    "license",
    "license.md",
    "makefile",
    "justfile",
    "dockerfile",
    "containerfile",
    "pyproject.toml",
    "package.json",
    "cargo.toml",
    "go.mod",
    "requirements.txt",
}

TRASH_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    "node_modules",
    "dist",
    "build",
    "target",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    ".idea",
    ".vscode",
    "coverage",
}

TRASH_FILE_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".svg",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".mp3",
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".sqlite",
    ".db",
}

LLM_PREAMBLE = """REFCTX PROTOCOL INITIATED
=======================
I am using the repo-local `scripts/refctx.py` helper to load external reference docs.

Workflow:
1. Scout first (tree/list) to build structure awareness.
2. Spy next (`-s`) to inspect headers/imports before loading full files.
3. Extract exact files only when needed.
4. Cite exact paths and avoid guessing missing details.
"""


@dataclass(slots=True)
class ResolvedTargets:
    root: Path
    targets: list[Path]


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CTX-inspired local reference context loader for agents (no deps, stdout only).",
        epilog=(
            "Examples:\n"
            "  python scripts/refctx.py --list\n"
            "  python scripts/refctx.py --find pydantic\n"
            "  python scripts/refctx.py -t -d 2 pydantic-ai/docs\n"
            "  python scripts/refctx.py -s 80 pydantic-ai/docs\n"
            "  python scripts/refctx.py pydantic-ai/docs/getting-started\n"
            "  python scripts/refctx.py -t -d 1 pydantic-ai\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--list", action="store_true", help="List top-level entries in the reference root (or target dirs)."
    )
    mode.add_argument("-l", "--llm", action="store_true", help="Print LLM preamble and a tree map.")
    mode.add_argument("-t", "--tree", action="store_true", help="Print a tree map only.")
    mode.add_argument("-s", "--spy", type=int, metavar="N", help="Print top N lines for matched files.")
    mode.add_argument("--find", metavar="QUERY", help="Find files/dirs whose path contains QUERY (case-insensitive).")

    parser.add_argument("targets", nargs="*", help="Paths under the reference root.")
    parser.add_argument(
        "-d",
        "--depth",
        type=int,
        default=DEFAULT_DEPTH,
        help=f"Traversal depth (default: {DEFAULT_DEPTH}, 0=root only, -1=infinite).",
    )
    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Bypass line-count limit for full extraction mode.",
    )
    parser.add_argument(
        "-M",
        "--max-bytes",
        type=int,
        default=DEFAULT_MAX_BYTES,
        help=f"Skip files larger than this many bytes (default: {DEFAULT_MAX_BYTES}).",
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help=f"Skip files longer than this in extract mode unless --force (default: {DEFAULT_MAX_LINES}).",
    )
    parser.add_argument(
        "-P",
        "--print-limit",
        type=int,
        default=DEFAULT_PRINT_LIMIT,
        help=f"Max lines/items to print in previews (default: {DEFAULT_PRINT_LIMIT}).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = DEFAULT_ROOT.resolve()

    if not root.exists() and requires_existing_root(args.targets):
        print(f"refctx: reference root not found: {root}", file=sys.stderr)
        print(
            "refctx: create it and place cloned/downloaded docs there (e.g. ~/Documents/References).", file=sys.stderr
        )
        return 2

    try:
        resolved = resolve_targets(root=root, target_args=args.targets)
    except ValueError as exc:
        print(f"refctx: {exc}", file=sys.stderr)
        return 2

    if args.list:
        return run_list(resolved, print_limit=args.print_limit)
    if args.find:
        return run_find(resolved, query=args.find, depth=args.depth, print_limit=args.print_limit)
    if args.llm:
        print(LLM_PREAMBLE.rstrip())
        print()
        print_tree(resolved.targets, base_root=root, depth=args.depth, print_limit=args.print_limit)
        return 0
    if args.tree:
        print_tree(resolved.targets, base_root=root, depth=args.depth, print_limit=args.print_limit)
        return 0
    if args.spy is not None:
        return run_extract(
            resolved,
            depth=args.depth,
            spy_lines=args.spy,
            max_bytes=args.max_bytes,
            max_lines=args.max_lines,
            force=args.force,
        )

    return run_extract(
        resolved,
        depth=args.depth,
        spy_lines=None,
        max_bytes=args.max_bytes,
        max_lines=args.max_lines,
        force=args.force,
    )


def requires_existing_root(target_args: Sequence[str]) -> bool:
    if not target_args:
        return True
    return any(not Path(raw).expanduser().is_absolute() for raw in target_args)


def resolve_targets(*, root: Path, target_args: Sequence[str]) -> ResolvedTargets:
    if not target_args:
        return ResolvedTargets(root=root, targets=[root])

    targets: list[Path] = []
    for raw in target_args:
        candidate = Path(raw).expanduser()
        path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()

        if not path.exists():
            message = f"target not found: {raw}"
            raise ValueError(message)

        if not is_relative_to(path, root):
            message = f"target outside reference root: {path}"
            raise ValueError(message)
        targets.append(path)
    return ResolvedTargets(root=root, targets=targets)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def normalize_depth(depth: int) -> int:
    if depth == -1:
        return 1_000_000
    if depth < -1:
        return 0
    return depth


def iter_tree_entries(root: Path, max_depth: int) -> Iterator[tuple[Path, int]]:
    if not root.exists():
        return

    normalized = normalize_depth(max_depth)
    yield root, 0
    if not root.is_dir() or normalized == 0:
        return

    def walk(current: Path, depth: int) -> Iterator[tuple[Path, int]]:
        if depth >= normalized:
            return
        try:
            entries = sorted(current.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return

        for entry in entries:
            if entry.is_symlink():
                continue
            if entry.name in TRASH_DIR_NAMES and entry.is_dir():
                continue
            if entry.is_file() and should_skip_file(entry):
                continue
            yield entry, depth + 1
            if entry.is_dir():
                yield from walk(entry, depth + 1)

    yield from walk(root, 0)


def print_tree(targets: Sequence[Path], *, base_root: Path, depth: int, print_limit: int) -> None:
    for index, target in enumerate(targets):
        if index:
            print()
        rel = display_path(target, base_root)
        print(f"# Tree: {rel}")
        lines = list(format_tree_lines(target, base_root=base_root, depth=depth))
        if len(lines) > print_limit:
            for line in lines[:print_limit]:
                print(line)
            remaining = len(lines) - print_limit
            print(f"... [and {remaining} more entries]")
        else:
            for line in lines:
                print(line)


def format_tree_lines(root: Path, *, base_root: Path, depth: int) -> Iterator[str]:
    normalized = normalize_depth(depth)
    if not root.exists():
        yield f"[missing] {root}"
        return
    yield display_path(root, base_root)
    if not root.is_dir() or normalized == 0:
        return
    yield from _format_tree_children(root, prefix="", current_depth=0, max_depth=normalized, base_root=base_root)


def _format_tree_children(
    directory: Path,
    *,
    prefix: str,
    current_depth: int,
    max_depth: int,
    base_root: Path,
) -> Iterator[str]:
    if current_depth >= max_depth:
        return
    try:
        entries = sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        yield f"{prefix}[permission denied]"
        return

    visible: list[Path] = []
    for entry in entries:
        if entry.is_symlink():
            continue
        if entry.is_dir() and entry.name in TRASH_DIR_NAMES:
            continue
        if entry.is_file() and should_skip_file(entry):
            continue
        visible.append(entry)

    for idx, entry in enumerate(visible):
        branch = "└── " if idx == len(visible) - 1 else "├── "
        next_prefix = f"{prefix}{'    ' if idx == len(visible) - 1 else '│   '}"
        suffix = "/" if entry.is_dir() else ""
        yield f"{prefix}{branch}{entry.name}{suffix}"
        if entry.is_dir():
            yield from _format_tree_children(
                entry,
                prefix=next_prefix,
                current_depth=current_depth + 1,
                max_depth=max_depth,
                base_root=base_root,
            )


def run_find(resolved: ResolvedTargets, *, query: str, depth: int, print_limit: int) -> int:
    needle = query.casefold()
    matches: list[Path] = []
    for target in resolved.targets:
        for path, _ in iter_tree_entries(target, depth):
            if needle in str(path).casefold():
                matches.append(path)

    if not matches:
        print(f"# Find: no matches for {query!r}")
        return 1

    print(f"# Find: {query!r} ({len(matches)} matches)")
    for path in matches[:print_limit]:
        marker = "/" if path.is_dir() else ""
        print(f"- {display_path(path, resolved.root)}{marker}")
    if len(matches) > print_limit:
        print(f"- ... [{len(matches) - print_limit} more matches]")
    return 0


def run_list(resolved: ResolvedTargets, *, print_limit: int) -> int:
    """List immediate children for each target directory (or the file itself)."""
    for index, target in enumerate(resolved.targets):
        if index:
            print()
        if target.is_file():
            print(f"# List: {display_path(target, resolved.root)}")
            print(f"- {display_path(target, resolved.root)}")
            continue

        print(f"# List: {display_path(target, resolved.root)}")
        try:
            entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            print("- [permission denied]")
            continue

        visible = [entry for entry in entries if not entry.is_symlink() and not should_skip_list_entry(entry)]
        for entry in visible[:print_limit]:
            marker = "/" if entry.is_dir() else ""
            print(f"- {display_path(entry, resolved.root)}{marker}")
        if len(visible) > print_limit:
            print(f"- ... [{len(visible) - print_limit} more entries]")
    return 0


def run_extract(
    resolved: ResolvedTargets,
    *,
    depth: int,
    spy_lines: int | None,
    max_bytes: int,
    max_lines: int,
    force: bool,
) -> int:
    files = collect_files(resolved.targets, depth=depth)
    if not files:
        print("# refctx: no eligible text files found")
        return 1

    header_mode = f"SPY ({spy_lines} lines)" if spy_lines is not None else "EXTRACT"
    print(f"# REFCTX {header_mode}")
    print(f"# Root: {resolved.root}")
    print("# Files:")
    for file_path in files:
        print(f"- {display_path(file_path, resolved.root)}")
    print("\n---")

    skipped = 0
    for file_path in files:
        rel = display_path(file_path, resolved.root)
        try:
            stat = file_path.stat()
        except OSError as exc:
            print(f"\n--- File: {rel} [SKIPPED - stat error: {exc}] ---\n")
            skipped += 1
            continue

        if stat.st_size > max_bytes:
            print(f"\n--- File: {rel} [SKIPPED - SIZE {stat.st_size} > {max_bytes}] ---\n")
            skipped += 1
            continue

        try:
            raw = file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"\n--- File: {rel} [SKIPPED - non-UTF8 text] ---\n")
            skipped += 1
            continue
        except OSError as exc:
            print(f"\n--- File: {rel} [SKIPPED - read error: {exc}] ---\n")
            skipped += 1
            continue

        lines = raw.splitlines()
        if spy_lines is None and not force and len(lines) > max_lines:
            print(f"\n--- File: {rel} [SKIPPED - LINES {len(lines)} > {max_lines}; use --force] ---\n")
            skipped += 1
            continue

        print(f"\n--- File: {rel} ---")
        if spy_lines is not None:
            for line in lines[:spy_lines]:
                print(line)
            if len(lines) > spy_lines:
                print("\n[Truncated]")
        else:
            print(raw, end="" if raw.endswith("\n") else "\n")

    if skipped:
        print(f"\n# Skipped: {skipped}")
    return 0


def collect_files(targets: Sequence[Path], *, depth: int) -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    for target in targets:
        if target.is_file():
            if is_allowed_file(target) and target not in seen:
                files.append(target)
                seen.add(target)
            continue

        for path, file_depth in iter_tree_entries(target, depth):
            if file_depth == 0 or not path.is_file():
                continue
            if path in seen or not is_allowed_file(path):
                continue
            files.append(path)
            seen.add(path)
    return files


def is_allowed_file(path: Path) -> bool:
    if should_skip_file(path):
        return False
    name = path.name
    lower_name = name.casefold()
    if lower_name in SPECIAL_FILENAMES:
        return True
    if lower_name.startswith("readme."):
        return True
    suffix = path.suffix.casefold()
    return suffix in ALLOWED_EXTENSIONS


def should_skip_file(path: Path) -> bool:
    lower_name = path.name.casefold()
    if lower_name in {"uv.lock", "package-lock.json", "yarn.lock"}:
        return True
    suffix = path.suffix.casefold()
    return suffix in TRASH_FILE_SUFFIXES


def should_skip_list_entry(path: Path) -> bool:
    if path.is_dir():
        return path.name in TRASH_DIR_NAMES
    return should_skip_file(path)


def display_path(path: Path, root: Path) -> str:
    if is_relative_to(path, root):
        return str(path.relative_to(root)) or "."
    return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
