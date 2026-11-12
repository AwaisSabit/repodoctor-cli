# RepoDoctor

A command-line repository health checker for Python projects.

RepoDoctor scans a folder **read-only** — it never modifies, deletes, or
executes anything in the scanned repository — and reports basic project
hygiene: how many files and Python files it found, whether a README
exists, and any simple findings (for example, a missing README).

> Built as part of a 30-day portfolio challenge, Nov–Dec 2026.
> This is the working skeleton: package layout, CLI entry point,
> read-only scanner, basic checks, text/JSON output, and pytest tests.
> More checks (dependency files, test layout, large files, syntax
> checks, strict mode) are planned.

## Problem

Developers often clone or start a Python repository that is missing
basic hygiene — no README, no tests, no dependency file. RepoDoctor
gives a quick, honest first look so those gaps are visible before
anyone spends time on the code.

## Install

Requires Python 3.11 or newer.

```bash
git clone https://github.com/AwaisSabit/repodoctor-cli.git
cd repodoctor-cli
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e .[test]           # editable install, including pytest
```

## Usage

```bash
repodoctor .
repodoctor ./my-project
repodoctor ./my-project --format json
python -m repodoctor --help
python -m repodoctor --version
```

Example output (`repodoctor .` on this repository):

```text
RepoDoctor — /home/awais/repodoctor-cli
  Files:        19
  Python files: 9
  README:       yes (README.md)
  Findings:     none
```

Exit codes: `0` means the scan completed (even if findings are
warnings); `2` means the scan itself failed, for example the target
does not exist.

## What it checks

- README exists
- The directory is not empty
- At least one Python file exists (informational)

Findings are heuristics — warnings worth a look, not security verdicts.

## Tests

```bash
python -m pytest -q
```

## Limitations

- Only the three basic checks above; no dependency-file, test-layout,
  large-file, or syntax checks yet (planned).
- No strict mode / non-zero exit on findings yet (planned).
- No configuration file yet.
- The scanner skips `.git`, `.venv`, `venv`, `__pycache__`, `.tox`,
  and `.mypy_cache` directories when counting files.

## License

MIT — see [LICENSE](LICENSE).
