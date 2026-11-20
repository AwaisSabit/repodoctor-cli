# RepoDoctor

A command-line repository health checker for Python projects.

RepoDoctor scans a folder **read-only** — it never modifies, deletes, or
executes anything in the scanned repository — and reports basic project
hygiene: how many files and Python files it found, whether a README,
a `.gitignore`, a dependency file and tests exist, any files larger
than 1 MB, any generated directories not covered by `.gitignore`,
any Python files that do not compile, any reminder markers left in
text files, and any simple findings (for example, a missing README).

> Built as part of a 30-day portfolio challenge, Nov–Dec 2026.
> This is the working tool: package layout, CLI entry point,
> read-only scanner, ten checks, text/JSON output, strict mode,
> and pytest tests. More checks are planned.

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
repodoctor ./my-project --no-color
repodoctor ./my-project --strict
python -m repodoctor --help
python -m repodoctor --version
```

Example output (`repodoctor .` on this repository):

```text
RepoDoctor — /home/awais/repodoctor-cli
  Files:        21
  Python files: 10
  README:       yes (README.md)
  Gitignore:    yes (.gitignore)
  Dependency:   pyproject.toml
  Test files:   3
  Large files:  none
  Generated dirs: .pytest_cache, .venv, src/repodoctor/__pycache__, tests/__pycache__
  Syntax errors: none
  TODO markers: none
  Findings:     none
  Found no findings.
```

Example output on a folder with findings — findings are grouped by
severity, errors first, then warnings, then informational notes, with
a summary count at the end:

```text
RepoDoctor — /home/awais/my-project
  Files:        2
  Python files: 1
  README:       no
  Gitignore:    no
  Dependency:   no
  Test files:   0
  Large files:  none
  Generated dirs: none
  Syntax errors: broken.py: line 1
  TODO markers: notes.txt (1)
  Findings:
    Errors (1)
      [error] syntax-error: File broken.py has a Python syntax error on line 1: invalid syntax.
    Warnings (4)
      [warning] missing-readme: No README file found. Add a README.md describing what this project does.
      [warning] missing-gitignore: No .gitignore file found. Add one so virtual environments and cache files are not committed by accident.
      [warning] missing-dependency-file: No dependency file found (pyproject.toml, requirements.txt, setup.py or setup.cfg). Add one so others can install this project's dependencies.
      [warning] missing-tests: No tests directory or test files found. Add a tests/ folder with at least one test so changes can be checked.
    Notes (1)
      [info] todo-markers: File notes.txt contains 1 reminder marker (TODO, FIXME, XXX or HACK). This is information only, not a problem.
  Found 1 error, 4 warnings and 1 note.
```

When the text output goes to a terminal, the severity labels
(`[error]`, `[warning]`, `[info]`) are coloured; piped or redirected
output stays plain text. Use `--no-color` to turn the colour off.

## Strict mode

`--strict` is for scripts and CI, where a scan that found anything
should fail the step. It works with both text and JSON output:

```bash
repodoctor ./my-project --strict
repodoctor ./my-project --strict --format json
```

The full report is still printed — only the exit code changes. Any
finding counts: an error, a warning, or an informational note.

## Exit codes

- `0` — the scan ran. Without `--strict`, findings do not change
  the exit code; with `--strict`, `0` means the scan found nothing.
- `1` — strict mode was given (`--strict`) and the scan found at
  least one finding (an error, a warning or a note).
- `2` — a usage problem: the command line was wrong (for example a
  bad flag — argparse exits 2 on bad arguments), or the folder to
  scan does not exist.

## JSON output

`repodoctor ./my-project --format json` prints the same scan as a
JSON document, for use in scripts and CI. The top-level fields are:

- `tool` — always `"repodoctor"`.
- `schema_version` — the version of this JSON format, starting at 1.
  It changes only when a field is added, removed or renamed, so a
  script can check it before reading the rest.
- `tool_version` — the RepoDoctor version that produced the report.
- `target` — the folder that was scanned.
- `total_files` and `python_files` — how many files were found, and
  how many of them are Python files. `has_python_files` says
  whether any Python files were found at all.
- `files` — the list of files found, as paths relative to the target.
- `has_readme` and `readme_path` — whether a README exists at the
  repository root, and its path when it does.
- `has_gitignore`, `gitignore_path`, `gitignore_entries` and
  `gitignore_missing_exclusions` — whether a `.gitignore` exists at
  the root, its path, the entries it contains, and the common Python
  exclusions (`.venv/`, `__pycache__/`) it is missing.
- `dependency_file` — the dependency file found
  (`pyproject.toml`, `requirements.txt`, `setup.py` or `setup.cfg`),
  or nothing when there is none.
- `test_files` and `has_tests` — how many test files were found, and
  whether there are any.
- `large_files` — each file over 1 MB, with its path, its size in
  bytes and a human-readable size.
- `generated_dirs` — generated or cache directories that exist
  (`.venv`, `__pycache__` and the rest).
- `syntax_errors` — Python files that do not compile, with the file,
  the line number and the error message.
- `todo_markers` — files containing reminder markers, with the file
  and how many markers it has.
- `findings` — the same findings as the text report, in the same
  order, each with a stable `code`, a plain-English `message`, a
  `severity` (`"error"`, `"warning"` or `"info"`) and a `path` when
  the finding is about one file.
- `summary` — the finding counts: `total` findings, plus `errors`,
  `warnings` and `notes` (informational findings). These numbers
  match the closing summary line of the text report, so the two
  formats always agree.

Short example (a folder with two files, a missing README, no
`.gitignore`, no dependency file and no tests):

```json
{
  "tool": "repodoctor",
  "schema_version": 1,
  "tool_version": "0.1.0",
  "target": "/home/awais/my-project",
  "total_files": 2,
  "python_files": 1,
  "has_python_files": true,
  "files": ["app.py", "notes.txt"],
  "has_readme": false,
  "readme_path": null,
  "has_gitignore": false,
  "gitignore_path": null,
  "gitignore_entries": [],
  "gitignore_missing_exclusions": [],
  "dependency_file": null,
  "test_files": 0,
  "has_tests": false,
  "large_files": [],
  "generated_dirs": [],
  "syntax_errors": [],
  "todo_markers": [],
  "findings": [
    {
      "code": "missing-readme",
      "message": "No README file found. Add a README.md describing what this project does.",
      "severity": "warning",
      "path": null
    }
  ],
  "summary": {
    "total": 4,
    "errors": 0,
    "warnings": 4,
    "notes": 0
  }
}
```

(The example above shows only the first finding; the full output
lists all four warnings.)

## What it checks

- README exists
- The directory is not empty
- At least one Python file exists (informational)
- A `.gitignore` file exists, and it contains the common Python
  exclusions `.venv/` and `__pycache__/`
- A dependency file exists (`pyproject.toml`, `requirements.txt`,
  `setup.py` or `setup.cfg`) — the one found is named in the output
- A tests directory or test files exist — the number of test files
  found is shown in the output
- No file is larger than 1 MB — each file over the limit is listed
  with its human-readable size (for example, "1.2 MB")
- Generated or cache directories (`__pycache__`, `.venv`, `venv`,
  `.tox`, `.mypy_cache`, `.pytest_cache`, `dist`, `build`) are listed
  in `.gitignore` — a directory that exists but is not covered by
  `.gitignore` is flagged, so it is not committed by accident
- Every Python file compiles — a file with a syntax error is
  reported as an error with its file and line number. Files are
  only compiled, never run, so broken or unsafe code is safe to scan
- Reminder markers (TODO, FIXME, XXX and HACK) in text files are
  counted per file and reported as information only, not as
  problems. A marker is one of those words followed by a colon.

Findings are heuristics — warnings worth a look, not security verdicts.

In the text report, findings are grouped by severity — errors first,
then warnings, then informational notes — each group under its own
heading, with a summary count at the end. The JSON report carries the
same findings, in the same order, with the same severities.

Paths are the same on every platform: every path in the text and
JSON output uses forward slashes, even when the scan ran on Windows,
so a report from Windows matches one from macOS or Linux. A
`.gitignore` written on Windows (with backslash separators) is read
the same way as one written with forward slashes, and generated
directories are recognised with either separator.

## Tests

```bash
python -m pytest -q
```

The suite covers the scanner, every check, both reporters and
strict mode with unit tests, plus end-to-end tests
(`tests/test_cli_integration.py`) that run the real installed
`repodoctor` command as a subprocess against temporary folders —
including a scan of the tool's own repository, which must come back
clean. Cross-platform path handling has its own tests
(`tests/test_cross_platform.py`), and the read-only promise has its
own (`tests/test_readonly.py`): a scan must leave the scanned folder
byte-identical, create no bytecode files, and succeed on a
read-only directory.

## Limitations

- Only the ten checks above.
- No configuration file yet.
- The scanner skips `.git`, `.venv`, `venv`, `__pycache__`, `.tox`,
  `.mypy_cache`, `.pytest_cache`, `dist` and `build` directories when
  counting files, so large files inside those directories are never
  flagged; generated directories themselves are still reported.

## License

MIT — see [LICENSE](LICENSE).
