"""Output formatters for RepoDoctor results.

Reporters take a :class:`~repodoctor.models.ScanResult` and return a
string; they never print or write files themselves, so the CLI stays
in charge of output and exit codes.
"""

from __future__ import annotations

import json

from .models import ScanResult


def format_summary(result: ScanResult) -> str:
    """Return a short human-readable summary of a scan."""
    lines = [
        f"RepoDoctor — {result.target}",
        f"  Files:        {result.total_files}",
        f"  Python files: {result.python_files}",
        f"  README:       {'yes' + (f' ({result.readme_path})' if result.readme_path else '') if result.has_readme else 'no'}",
    ]
    if result.findings:
        lines.append("  Findings:")
        for finding in result.findings:
            lines.append(f"    [{finding.severity}] {finding.code}: {finding.message}")
    else:
        lines.append("  Findings:     none")
    return "\n".join(lines)


def format_json(result: ScanResult) -> str:
    """Return the scan result as a JSON document (for CI use)."""
    payload = {
        "target": str(result.target),
        "total_files": result.total_files,
        "python_files": result.python_files,
        "has_readme": result.has_readme,
        "readme_path": str(result.readme_path) if result.readme_path else None,
        "findings": [
            {
                "code": finding.code,
                "message": finding.message,
                "severity": finding.severity,
                "path": str(finding.path) if finding.path else None,
            }
            for finding in result.findings
        ],
    }
    return json.dumps(payload, indent=2)
