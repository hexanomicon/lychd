"""Read the private Reach operator diagnostic archive without effect or recovery authority."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn

if __package__:
    from scripts.reach_trace_archive import TraceArchiveError, query_archive
else:
    from reach_trace_archive import TraceArchiveError, query_archive


class _Parser(argparse.ArgumentParser):
    """Keep malformed local CLI arguments out of diagnostic output."""

    def error(self, message: str) -> NoReturn:
        del message
        self.exit(2, "reach_trace_refused\n")


def parser() -> argparse.ArgumentParser:
    """Expose only fixed identity, time and failure selectors."""
    result = _Parser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("recent", "show", "query", "runs"):
        child = commands.add_parser(command)
        child.add_argument("--archive-dir", type=Path, required=True)
        child.add_argument("--limit", type=int, default=100)
        child.add_argument("--generation")
        child.add_argument("--since")
        child.add_argument("--until")
        child.add_argument("--failures", action="store_true")
        identity = child.add_mutually_exclusive_group(required=command == "show")
        identity.add_argument("--run-id")
        identity.add_argument("--request-id")
        identity.add_argument("--platform-event-id")
        identity.add_argument("--call-id")
        identity.add_argument("--latest", action="store_true")
    return result


def main(argv: list[str] | None = None) -> int:
    """Write JSON observations or one fixed refusal, never a driver exception."""
    args = parser().parse_args(argv)
    try:
        result = query_archive(
            args.archive_dir,
            run_id=args.run_id,
            request_id=args.request_id,
            platform_event_id=args.platform_event_id,
            call_id=args.call_id,
            generation=args.generation,
            since=args.since,
            until=args.until,
            failures=args.failures,
            limit=args.limit,
            latest=args.latest,
            runs=args.command == "runs",
        )
    except TraceArchiveError:
        sys.stderr.write("reach_trace_refused\n")
        return 1
    sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
