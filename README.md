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
> read-only scanner, ten checks, text/JSON output, and pytest tests.
> More checks (strict mode) are planned.

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

Exit codes: `0` means the scan completed (even if findings are
warnings); `2` means the scan itself failed, for example the target
does not exist.

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

## Tests

```bash
python -m pytest -q
```

## Limitations

- Only the ten checks above.
- No strict mode / non-zero exit on findings yet (planned).
- No configuration file yet.
- The scanner skips `.git`, `.venv`, `venv`, `__pycache__`, `.tox`,
  `.mypy_cache`, `.pytest_cache`, `dist` and `build` directories when
  counting files, so large files inside those directories are never
  flagged; generated directories themselves are still reported.

## License

MIT — see [LICENSE](LICENSE).
