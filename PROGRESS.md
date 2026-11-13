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
