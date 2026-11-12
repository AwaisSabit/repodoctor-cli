"""Command-line interface for RepoDoctor.

Usage:
    repodoctor .
    repodoctor ./my-project --format json
    repodoctor --help
    repodoctor --version

The CLI is deliberately built on :mod:`argparse` only (no third-party
CLI framework on Day 1). It scans the target read-only, runs the basic
checks, prints a summary, and exits 0 on a successful scan — even when
findings are warnings. A non-zero exit means the scan itself failed
(for example, the target does not exist).
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .checks import run_checks
from .reporters import format_json, format_summary
from .scanner import scan_path


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for the ``repodoctor`` command."""
    parser = argparse.ArgumentParser(
        prog="repodoctor",
        description="Check the basic health of a Python repository (read-only).",
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Directory to scan (default: current directory).",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format: human-readable text (default) or JSON for CI.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the RepoDoctor version and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the process exit code (0 on success)."""
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        result = scan_path(Path(args.target))
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"repodoctor: error: {exc}", file=sys.stderr)
        return 2

    run_checks(result)
    if args.format == "json":
        print(format_json(result))
    else:
        print(format_summary(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
