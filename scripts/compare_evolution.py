"""Read one offline comparison from stdin; completion grants no acceptance.

Exit 0 records a complete comparison or rejection, 1 a blocked comparison, and
2 refused input. No referenced artifact, configuration or runtime is opened.
"""

from __future__ import annotations

import sys

from lychd.domain.evolution import (
    MAX_INPUT_BYTES,
    MAX_OUTPUT_BYTES,
    compare_history,
    decode_packet,
)


def main() -> int:
    """Consume bounded stdin and emit a bounded report with fixed diagnostics."""
    if len(sys.argv) != 1:
        sys.stderr.write("comparison input refused\n")
        return 2
    try:
        packet = decode_packet(sys.stdin.buffer.read(MAX_INPUT_BYTES + 1))
        report = compare_history(packet.admission, packet.proposal)
        output = report.model_dump_json() + "\n"
    except (ValueError, RecursionError, OSError):
        sys.stderr.write("comparison input refused\n")
        return 2
    if len(output.encode("utf-8")) > MAX_OUTPUT_BYTES:
        sys.stderr.write("comparison input refused\n")
        return 2
    sys.stdout.write(output)
    return 1 if report.outcome == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
