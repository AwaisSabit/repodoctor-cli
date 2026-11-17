"""Command-line interface for RepoDoctor.

Usage:
    repodoctor .
    repodoctor ./my-project --format json
    repodoctor ./my-project --no-color
    repodoctor --help
    repodoctor --version

The CLI is deliberately built on :mod:`argparse` only (no third-party
CLI framework on Day 1). It scans the target read-only, runs the basic
checks, prints a summary, and exits 0 on a successful scan — even when
findings are warnings. A non-zero exit means the scan itself failed
(for example, the target does not exist) or, in strict mode, that the
scan found anything at all. Severity labels in the text
report are coloured only when the output goes to a terminal; use
``--no-color`` to turn that off.
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
        "--strict",
        action="store_true",
        help="Exit 1 when the scan finds anything (an error, a warning "
        "or a note). Without this flag, findings do not change the "
        "exit code. The full report is still printed either way.",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Do not colour severity labels in the text report, even "
        "when the output goes to a terminal.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show the RepoDoctor version and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI and return the process exit code.

    Exit codes: ``0`` when the scan ran (findings do not change the
    exit code unless ``--strict`` was given), ``1`` when ``--strict``
    was given and the scan found anything, ``2`` when the scan itself
    failed (for example, the target does not exist) or the command
    line was wrong.
    """
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
        # Colour severity labels only when the output goes to a
        # terminal; piped or redirected output stays plain text.
        use_color = sys.stdout.isatty() and not args.no_color
        print(format_summary(result, use_color=use_color))
    if args.strict and result.findings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
