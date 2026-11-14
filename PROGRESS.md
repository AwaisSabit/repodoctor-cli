# RepoDoctor — Progress

## Day 1 — 2026-11-12 (Plan Day 1: package skeleton, CLI entry point)

### Done
- Created the repository layout from the plan:
  `src/repodoctor/` (`__init__.py`, `__main__.py`, `cli.py`, `scanner.py`,
  `checks.py`, `models.py`, `reporters.py`), `tests/`, `pyproject.toml`,
  `README.md`, `LICENSE` (MIT), `.gitignore`.
- CLI works with `argparse` only (no Typer on Day 1):
  `python -m repodoctor --help`, `python -m repodoctor --version`,
  `repodoctor .` and `repodoctor . --format json` all work after an
  editable install; the `repodoctor` console-script entry point is
  registered in `pyproject.toml`.
- Read-only scanner (`scanner.py`): walks the target with `pathlib`,
  skips `.git`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`,
  `.tox`, `.mypy_cache`; counts files and Python files; detects a
  root-level README. It never writes to, deletes, or executes anything
  in the scanned directory (covered by a test).
- Basic checks (`checks.py`): missing README, empty directory,
  no Python files (info). Text and JSON reporters (`reporters.py`).
- Two real bugs found and fixed while testing, before committing:
  1. `pyproject.toml` used the `License :: OSI Approved :: MIT License`
     classifier together with `license = "MIT"`, which current
     setuptools rejects (PEP 639). Removed the classifier.
  2. The scanner counted `.pytest_cache/README.md` as the project
     README. Fixed: only a root-level README counts, and
     `.pytest_cache` is now a skipped directory. A test covers this.

### Tests / checks run (Day 1)
- Command: `python -m venv .venv && .venv/bin/pip install -e ".[test]"`
  then `.venv/bin/python -m pytest -q`
- Result: **14 passed in 0.14s** (13 CLI/scanner tests + 1 regression
  test for the nested-README fix). Python 3.12.3.
- `.venv/bin/python -m repodoctor --help` — exit 0.
- `.venv/bin/python -m repodoctor --version` — `repodoctor 0.1.0`.
- `.venv/bin/repodoctor .` — exit 0; reported 19 files, 9 Python
  files, README yes (`README.md`), no findings.
- `.venv/bin/repodoctor . --format json` — valid JSON, same facts.
- `git diff --check` — clean. No secrets in the tree (no tokens,
  keys, passwords, or `.env` files); `.venv/` is ignored.

### Commits (local only — NOT pushed)
- GitHub is not connected yet, so there is no remote. Local commits
  only; nothing was pushed. See `git log` for hashes.
- Commit 1: `Create the RepoDoctor tool with a working command line`
- Commit 2: `Add tests for the RepoDoctor scanner and command line, and fix the README check`

### Next steps — Day 2 (plan)
- Parse target path and display help/version — already done on Day 1,
  so Day 2 can start the Day 3 work early: finding/result data models
  are in place; extend the scanner/checks if needed and add the
  `.gitignore` and packaging checks (plan Day 4–5).
- Per the plan, the next checks to add are: `.gitignore` presence and
  common Python exclusions, dependency/packaging file presence
  (`pyproject.toml` / `requirements.txt`), and test-directory detection.
- When GitHub is connected, create the public `repodoctor-cli`
  repository under AwaisSabit, add it as remote, and push these
  commits (do not claim a push until the remote confirms it).

## Day 2 — 2026-11-13 (.gitignore, dependency-file and test checks)

### Done
- Added three new checks, keeping the scanner read-only (it only
  reads files; it never writes, deletes or runs anything in the
  scanned repo):
  1. `.gitignore` check — warns when no `.gitignore` exists, and
     warns when one exists but is missing common Python exclusions
     (`.venv/` and `__pycache__/`). Entries written without a
     trailing slash (`.venv`, `__pycache__`) still count.
  2. Dependency/packaging check — warns when no dependency file
     exists (`pyproject.toml`, `requirements.txt`, `setup.py` or
     `setup.cfg`); when one exists, the file found is shown in the
     output (`pyproject.toml` is preferred when several exist).
  3. Test-structure check — warns when no tests directory or test
     files exist; when they exist, the number of test files found
     is shown in the output. A test file is a `.py` file under a
     `tests/` or `test/` folder, or named `test_*.py` / `*_test.py`.
- Wired the new facts into the scanner (`ScanResult` now carries
  `has_gitignore`, `gitignore_missing_exclusions`, `dependency_file`
  and `test_files`), the checks (`checks.py`, six checks in total),
  and both reporters: the text summary shows Gitignore / Dependency
  / Test files lines, and the JSON output carries the same facts.
- Updated the README "What it checks" list and the example output
  in plain words, with no day numbers. The scanner still skips
  `.git`, `.venv`, `venv`, `__pycache__`, `.pytest_cache`, `.tox`
  and `.mypy_cache` when counting files.
- Updated two older tests whose exact finding lists changed now
  that the new warnings exist (a folder with only a README and a
  `.py` file now correctly reports the three new warnings too).

### Tests / checks run (Day 2)
- `.venv/bin/python -m pytest -q` → **31 passed in 0.22s**
  (14 existing tests + 17 new tests in `tests/test_checks.py`:
  missing/present `.gitignore`, both exclusion cases, missing and
  each present dependency file, missing/present tests, a healthy
  folder with no findings, and text + JSON CLI output).
- `.venv/bin/python -m repodoctor .` — exit 0; reported 21 files,
  10 Python files, README yes, Gitignore yes (`.gitignore`),
  Dependency `pyproject.toml`, Test files 3, no findings.
- `.venv/bin/python -m repodoctor . --format json` — valid JSON,
  same facts, `findings: []`.
- `git diff --check` — clean. No secrets in the tree; `.venv/` is
  ignored.

### Commits
- See `git log` for the hash. One commit, in plain English.
- Not pushed — the parent pushes to GitHub later.

### Next steps
- Large-file and syntax checks, then strict mode (non-zero exit on
  findings), per the plan.

## Day 3 — 2026-11-14 (large-file and generated-directory checks)

### Done
- Added two new checks, keeping the scanner read-only (it only
  reads files; it never writes, deletes or runs anything in the
  scanned repo):
  1. Large-file check — the scanner records the size of each file
     it finds and flags any file over 1 MB
     (`LARGE_FILE_THRESHOLD_BYTES = 1_048_576` in `scanner.py`),
     one warning per file with its relative path and a
     human-readable size (for example, "1.0 MB"). Files inside
     skipped directories (`.venv`, `.git`, `__pycache__` and the
     rest) are never flagged, since the scanner never walks those.
  2. Generated-directory check — the scanner records generated or
     cache directories that exist even though their contents are
     skipped (`__pycache__`, `.venv`, `venv`, `.tox`, `.mypy_cache`,
     `.pytest_cache`, `dist`, `build`). Each one that exists and is
     not covered by `.gitignore` is a warning suggesting it be
     added to `.gitignore`; an entry counts with or without a
     trailing slash, and it may name the directory or its full
     relative path. With no `.gitignore` at all, every generated
     directory found is a warning. A generated directory nested
     inside another skipped directory (for example
     `.venv/__pycache__`) is reported once, as the outer directory.
- `dist` and `build` are now skipped directories too, so their
  contents are not counted and large files inside them are never
  flagged — the same treatment the other generated directories
  already had.
- Wired the new facts into the scanner (`ScanResult` now carries
  `large_files`, `generated_dirs` and `gitignore_entries`), the
  checks (`checks.py`, eight checks in total), and both reporters:
  the text summary shows Large files and Generated dirs lines, and
  the JSON output carries `large_files` (path, size in bytes,
  human-readable size) and `generated_dirs`.
- Updated the README "What it checks" list, example output and
  Limitations to describe the two new checks, with no day numbers.
  The tool now has eight checks.

### Tests / checks run (Day 3)
- `.venv/bin/python -m pytest -q` → **43 passed in 0.38s**
  (31 existing tests + 12 new tests in `tests/test_checks.py`:
  a file just over 1 MB flagged and one just under not flagged,
  a large file inside `.venv` never flagged, a generated directory
  listed in `.gitignore` passing while an unlisted one warns, no
  `.gitignore` at all meaning generated directories are flagged,
  entries without a trailing slash still counting, a nested
  `__pycache__` covered by a name entry, a generated directory
  inside a skipped directory not recorded twice, a healthy folder
  still reporting no findings, and text + JSON CLI output showing
  the new facts).
- `.venv/bin/python -m repodoctor .` — exit 0; reported 21 files,
  10 Python files, README yes, Gitignore yes (`.gitignore`),
  Dependency `pyproject.toml`, Test files 3, Large files none,
  Generated dirs `.pytest_cache`, `.venv`,
  `src/repodoctor/__pycache__`, `tests/__pycache__`, no findings.
- `.venv/bin/python -m repodoctor . --format json` — valid JSON,
  same facts, `findings: []`.
- `git diff --check` — clean. No secrets in the tree; `.venv/` is
  ignored.

### Commits
- See `git log` for the hash. One commit, in plain English.
- Not pushed — the parent pushes to GitHub later.

### Next steps
- Syntax checks, then strict mode (non-zero exit on findings),
  per the plan.
