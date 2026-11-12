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
