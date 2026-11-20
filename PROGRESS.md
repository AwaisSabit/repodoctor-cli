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

## Day 4 — 2026-11-14 (Python syntax check and reminder-marker count)

### Done
- Added two new checks, keeping the scanner read-only (it only
  reads files; it never writes, deletes or runs anything in the
  scanned repo):
  1. Python syntax check — the scanner compiles every `.py` file
     it finds with `compile()` on the source text, which parses the
     file without executing it, so broken or unsafe code is safe to
     scan. A file with a `SyntaxError` is an error-level finding
     naming the file and the line number. Files that compile clean
     produce no finding. Files inside skipped directories (`.venv`,
     `.git`, `__pycache__` and the rest) are never checked, since
     the scanner never walks those. A file that cannot be read as
     UTF-8 text is skipped instead of being reported.
  2. Reminder-marker check — the scanner counts TODO, FIXME, XXX
     and HACK markers in text files (`.py`, `.md`, `.txt`, `.rst`,
     `.toml`, `.cfg`, `.ini`, `.json`, `.yaml`, `.yml`, `.js`,
     `.ts`, `.sh`, `.html`, `.css`) and reports one informational
     finding per file with the file and the count. Markers are
     notes left for later work, not problems, so they are never
     warnings or errors. A marker is one of those words followed
     by a colon, the usual style for a note in code or docs.
- Design note on the colon rule: matching the bare words would
  make the tool flag its own source (its marker list, its finding
  messages and its own docs all contain those words). Requiring
  the colon keeps the tool's own scan clean — its own repository
  still reports no findings — while catching the real convention.
  The tool's own docs and tests are written so they contain no
  literal marker text, for the same reason.
- Wired the new facts into the scanner (`ScanResult` now carries
  `syntax_errors` as (path, line, message) and `todo_markers` as
  (path, count)), the checks (`checks.py`, ten checks in total),
  and both reporters: the text summary shows Syntax errors and
  TODO markers lines, and the JSON output carries `syntax_errors`
  (path, line, message) and `todo_markers` (path, count).
- Updated the README "What it checks" list, example output,
  introduction and Limitations to describe the two new checks,
  with no day numbers. The tool now has ten checks.

### Tests / checks run (Day 4)
- `.venv/bin/python -m pytest -q` → **57 passed in 0.30s**
  (43 existing tests + 14 new tests in `tests/test_checks.py`:
  a broken file reported as an error with file and line, the
  line number named for a break on line 3, a clean file with no
  finding, code that would write a file if run proving it is only
  compiled (no file appears), two broken files each reported, a
  broken file inside `.venv` never flagged, markers counted per
  file across code and docs, a marker word with no colon not
  counted, marker words inside a binary file not counted, all
  four marker words counting, a clean folder with no marker
  findings, a healthy folder still reporting no findings, and
  text + JSON CLI output showing the new facts).
- `.venv/bin/python -m repodoctor .` — exit 0; reported 21 files,
  10 Python files, README yes, Gitignore yes (`.gitignore`),
  Dependency `pyproject.toml`, Test files 3, Large files none,
  Generated dirs `.pytest_cache`, `.venv`,
  `src/repodoctor/__pycache__`, `tests/__pycache__`, Syntax
  errors none, TODO markers none, no findings.
- `.venv/bin/python -m repodoctor . --format json` — valid JSON,
  same facts, `syntax_errors: []`, `todo_markers: []`,
  `findings: []`.
- `git diff --check` — clean. No secrets in the tree; `.venv/` is
  ignored.

### Commits
- See `git log` for the hashes. Two commits, in plain English.
- Not pushed — the parent pushes to GitHub later.

### Next steps
- Strict mode (non-zero exit on findings), per the plan.

## Day 5 — 2026-11-15 (text reporter grouped by severity)

### Done
- Reworked the text reporter (`reporters.py`) so findings are grouped
  by severity — errors first, then warnings, then informational notes
  — each group under its own heading with its count, for example
  "Errors (2)", "Warnings (1)", "Notes (3)". Each finding stays on
  its own line with its severity label and its plain-English message,
  and groups with no findings are left out. The summary facts section
  (files, README, gitignore, and the rest) still comes first, above
  the findings.
- Added a summary line at the end of the text output with the counts
  per severity, with correct singular/plural wording, for example
  "Found 2 errors, 1 warning and 3 notes." Severities with no
  findings are left out of the line. With no findings at all the
  report keeps its friendly "Findings: none" message and ends with
  "Found no findings."
- Colour, kept simple and safe: when the text output goes to a
  terminal, the severity labels are coloured (red for errors, yellow
  for warnings, cyan for notes); piped or redirected output is never
  coloured. A new `--no-color` flag turns the colour off. Headings
  and messages are never coloured.
- The JSON reporter is unchanged in structure: it already carries a
  severity per finding, and both reporters read the same findings,
  so the severities in the two formats always agree.
- Exit codes are unchanged: a scan with findings still exits 0 in
  non-strict mode (strict mode is planned for a later day).
- Updated the README with a grouped-output example, the colour and
  `--no-color` notes, and a short paragraph on how the two formats
  agree on severities. No day numbers in the README, as always.

### Tests / checks run (Day 5)
- `.venv/bin/python -m pytest -q` → **72 passed in 0.36s**
  (57 existing tests + 15 new tests in `tests/test_reporters.py`:
  findings grouped errors-then-warnings-then-notes whatever order
  they arrive in, each finding under its own group heading; the
  summary line counts right for a mixed set; singular/plural wording
  for one and several findings of each severity; zero findings
  keeping the "Findings: none" message with no group headings; a
  severity with no findings getting no heading; the facts section
  staying above the findings; the JSON output carrying the same
  findings with the same severities; colour appearing only when
  asked for and only on the severity label; CLI text output on a
  temp folder with findings showing all three groups and the
  summary line, still exiting 0; and the `--no-color` flag being
  accepted).
- `.venv/bin/python -m repodoctor .` — exit 0; reported 21 files,
  10 Python files, README yes, Gitignore yes (`.gitignore`),
  Dependency `pyproject.toml`, Test files 3, Large files none,
  Generated dirs `.pytest_cache`, `.venv`,
  `src/repodoctor/__pycache__`, `tests/__pycache__`, Syntax
  errors none, TODO markers none, "Findings: none",
  "Found no findings."
- A temp folder with a broken Python file, a missing README,
  `.gitignore`, dependency file and tests, and a file with a
  reminder marker showed the grouped output: "Errors (1)",
  "Warnings (4)", "Notes (1)", ending with
  "Found 1 error, 4 warnings and 1 note." — exit 0.
- `git diff --check` — clean. No secrets in the tree; `.venv/` is
  ignored. The new test file contains no literal reminder-marker
  text, so the tool still reports no findings on its own repository.

### Commits
- See `git log` for the hashes. Three commits, in plain English.
- Not pushed — the parent pushes to GitHub later.

### Next steps
- JSON reporter work, then strict mode (non-zero exit on findings),
  per the plan.

## Day 6 — 2026-11-16 (JSON reporter: version, summary, every scan fact)

### Done
- Versioned the JSON report so consumers can tell formats apart:
  the output now starts with `"tool": "repodoctor"`,
  `"schema_version": 1` (a new `JSON_SCHEMA_VERSION` constant in
  `reporters.py`, to bump only when a field is added, removed or
  renamed) and `"tool_version"` carrying the RepoDoctor version
  from `__init__.py` (currently `0.1.0`).
- Added a `"summary"` object to the JSON output with the total
  finding count and the counts per severity — `total`, `errors`,
  `warnings` and `notes` (informational findings are called notes,
  as in the text report). A new `summary_counts()` helper builds
  it, and its numbers match the text report's closing summary line
  ("Found 2 errors, 1 warning and 3 notes."), so both formats
  always agree. With no findings the summary is all zeros.
- Audited every `ScanResult` fact against the JSON output and fixed
  the gaps: the JSON now also carries the full `files` list (paths
  relative to the target), the `gitignore_entries` (sorted, so the
  output is stable) and `has_python_files`, alongside the facts it
  already had — target, file counts, README, gitignore path and
  missing exclusions, dependency file, test files, large files,
  generated directories, syntax errors, reminder markers and
  findings. Nothing in the JSON disagrees with the text output.
- Documented the JSON format in the README: a new "JSON output"
  section lists every top-level field and the summary object in
  plain words, with a short example taken from a real scan. No day
  numbers in the README, as always.
- Exit codes are unchanged: a scan with findings still exits 0 in
  non-strict mode (strict mode is planned for a later day).

### Tests / checks run (Day 6)
- `.venv/bin/python -m pytest -q` → **77 passed in 0.39s**
  (72 existing tests + 5 new tests in `tests/test_reporters.py`:
  the schema and tool version fields; the summary object counts
  for a mixed set and all zeros with no findings, matching the
  text summary line; every scan fact present in the JSON output in
  a consistent shape; and the CLI JSON output on a real folder
  with findings, its summary agreeing with the text output on the
  same folder).
- `.venv/bin/python -m repodoctor .` — exit 0; reported 22 files,
  11 Python files, README yes, Gitignore yes (`.gitignore`),
  Dependency `pyproject.toml`, Test files 4, Large files none,
  Generated dirs `.pytest_cache`, `.venv`,
  `src/repodoctor/__pycache__`, `tests/__pycache__`, Syntax
  errors none, TODO markers none, "Findings: none",
  "Found no findings."
- `.venv/bin/python -m repodoctor . --format json` — valid JSON,
  exit 0, `schema_version` 1, `tool_version` "0.1.0",
  `summary` all zeros, `files` listing all 22 files,
  `findings: []`.
- `git diff --check` — clean. No secrets in the tree; `.venv/` is
  ignored. The new tests contain no literal reminder-marker text,
  so the tool still reports no findings on its own repository.

### Commits
- See `git log` for the hashes. Three commits, in plain English.
- Not pushed — the parent pushes to GitHub later.

## Day 7 — 2026-11-17 (strict mode and exit codes)

### Done
- Added a `--strict` flag to the CLI (`cli.py`): when set, the scan
  exits 1 if it found ANY finding — an error, a warning or an
  informational note — and exits 0 when it found nothing. The flag
  works with both `--format text` and `--format json`, and the full
  report is still printed in strict mode; only the exit code
  changes. Non-strict behaviour is unchanged: a scan with findings
  still exits 0.
- The scanner stays read-only (it only reads files; it never writes,
  deletes or runs anything in the scanned repo), and the JSON schema
  is unchanged — `schema_version` stays 1, no field added, removed
  or renamed.
- Documented strict mode and the exit codes in the README: a new
  "Strict mode" section in the usage area, and an "Exit codes"
  section in plain words — 0 means the scan ran (findings do not
  change the exit code without `--strict`, or strict mode found
  nothing), 1 means strict mode found at least one finding, 2 means
  a usage problem (a bad command line, or the folder to scan does
  not exist). The Limitations list no longer says strict mode is
  planned. No day numbers in the README, as always.

### Tests / checks run (Day 7)
- `.venv/bin/python -m pytest -q` → **84 passed in 0.46s**
  (77 existing tests + 7 new tests in `tests/test_strict.py`:
  strict mode with findings exits 1 in text format and still
  prints the full report; strict mode with no findings exits 0;
  non-strict mode with findings still exits 0; strict mode with
  `--format json` exits 1 and still prints valid JSON with the
  findings and the summary; `--help` accepts the `--strict` flag;
  a folder whose only finding is a missing-README warning also
  fails strict mode; and a real subprocess run of
  `python -m repodoctor --strict` exits 1).
- `.venv/bin/python -m repodoctor .` — exit 0; reported 23 files,
  12 Python files, README yes, Gitignore yes (`.gitignore`),
  Dependency `pyproject.toml`, Test files 5, Large files none,
  Generated dirs `.pytest_cache`, `.venv`,
  `src/repodoctor/__pycache__`, `tests/__pycache__`, Syntax
  errors none, TODO markers none, "Findings: none",
  "Found no findings."
- `.venv/bin/python -m repodoctor . --strict` — exit 0 on the
  clean repo.
- `.venv/bin/python -m repodoctor . --strict --format json` —
  valid JSON, exit 0, `schema_version` 1, `findings: []`.
- A temp folder with a README and a `.py` file only, scanned with
  `--strict`, printed its 3 warnings and exited 1 (text and JSON).
- `git diff --check` — clean. No secrets in the tree; `.venv/` is
  ignored. The new tests contain no literal reminder-marker text,
  so the tool still reports no findings on its own repository.

### Commits
- See `git log` for the hashes. Three commits, in plain English.
- Not pushed — the parent pushes to GitHub later.

### Next steps
- Configuration file support, per the plan.

## Day 9 — 2026-11-19 (CLI integration tests: the real command, end to end)

### Done
- Added `tests/test_cli_integration.py` (14 tests): the first tests
  that run the real installed `repodoctor` command as a subprocess
  instead of calling the CLI functions in-process. Every test uses
  the `.venv/bin/repodoctor` console script (falling back to
  `python -m repodoctor` when the script is not there), with a
  30-second timeout and an explicit working directory, and every
  scanned folder is built in `tmp_path` — no network, no writes
  outside the temporary folders, except for reading the project
  root in the self-scan test.
- Coverage: `--help` exits 0 and names every flag; `--version`
  exits 0 and prints the package version; a text scan of a healthy
  temp folder exits 0 with "Found no findings."; a text scan of a
  messy temp folder (missing README, `.gitignore`, dependency file
  and tests, a Python file that does not compile, a notes file
  carrying one reminder marker) exits 0 non-strict, shows the
  "Errors (1)", "Warnings (4)", "Notes (1)" group headings and
  ends with "Found 1 error, 4 warnings and 1 note."; the same
  folder with `--strict` exits 1 and still prints the full report;
  the same folder with `--format json` exits 0 with valid JSON,
  `schema_version` 1 and a summary of 1 error, 4 warnings, 1 note
  matching the text counts; `--strict --format json` exits 1 with
  valid JSON and the same summary; `--format json` on a healthy
  folder has empty findings and an all-zero summary; a missing
  folder exits 2 with a clear error naming the folder and no
  traceback; an unknown flag exits 2 with a usage message and no
  traceback; `--no-color` output has no ANSI escape codes, and
  piped output is never coloured either; the scan is read-only
  (file contents and modification times unchanged, no new files
  created in the scanned folder); running with no target scans the
  current directory; and a scan of the tool's own repository exits
  0 with no findings — the real end-to-end proof the tool is clean
  on itself.
- One test expectation needed correcting while writing, and it was
  the test that was wrong, not the tool: the JSON findings list
  keeps check order (presence checks first, then the syntax and
  marker checks), while the text report groups the same findings
  by severity. That order is already locked in by an existing
  reporter test, so the integration test now asserts the check
  order and says so in a comment. No CLI code changed.
- The new test file contains no literal reminder-marker text — the
  marker in the temp notes file is built by joining string pieces —
  so the tool still reports no findings on its own repository.
- Updated the README "Tests" section to say the suite includes
  these end-to-end tests, with no day numbers.

### Tests / checks run (Day 9)
- `.venv/bin/python -m pytest -q` → **146 passed in 3.00s**
  (132 existing tests + 14 new integration tests; the new file
  alone runs in 2.63s, well under the 10-second budget).
- `.venv/bin/python -m repodoctor .` — exit 0; reported 26 files,
  15 Python files, README yes, Gitignore yes (`.gitignore`),
  Dependency `pyproject.toml`, Test files 8, Large files none,
  Generated dirs `.pytest_cache`, `.venv`,
  `src/repodoctor/__pycache__`, `tests/__pycache__`, Syntax
  errors none, TODO markers none, "Findings: none",
  "Found no findings."
- `.venv/bin/python -m repodoctor . --strict` — exit 0 on the
  clean repo.
- `git diff --check` — clean. No secrets in the tree; `.venv/` is
  ignored. The new tests contain no literal reminder-marker text,
  so the tool still reports no findings on its own repository.

### Commits
- See `git log` for the hashes. Two commits, in plain English.
- Not pushed — the parent pushes to GitHub later.

### Next steps
- Configuration file support, per the plan.

## Day 8 — 2026-11-18 (unit tests for every check)

### Coverage audit first
Every check in `checks.py` was audited against the existing tests
before anything new was written:

- Already covered by dedicated tests, left alone: the `.gitignore`
  check (missing, both exclusions present, each one missing, entries
  without a slash), the dependency-file check (missing, each of the
  four accepted files, `pyproject.toml` preferred), the test-structure
  check (missing, a `tests/` directory, a root `test_*.py` file), the
  large-file check (one byte over flagged, one byte under not flagged,
  a large file inside `.venv` never flagged), the generated-directory
  check (listed in `.gitignore`, not listed, no `.gitignore` at all,
  entry without a slash, a nested directory covered by a name entry,
  a nested directory not recorded twice), the syntax check (error on
  line 1, error on line 3, a clean file, code only compiled never
  run, two broken files, a broken file inside `.venv`), and the
  reminder-marker check (counted per file, a word with no colon, a
  binary file, all four marker words, a clean folder). The reporter
  and strict-mode tests were already covered too, and were not
  duplicated.
- Uncovered: no test had ever called a check function directly —
  every existing test reached the checks through `scan_path`, even
  though the checks are pure functions of a `ScanResult`. The
  no-Python-files check had no dedicated test at all (only an
  incidental appearance in a CLI JSON test), and the empty-directory
  and README checks had no direct tests either. A string of edge
  cases was also untested: a file exactly at the 1 MB threshold, the
  singular "1 reminder marker" wording, both `.gitignore` exclusions
  missing at once, a full-path `.gitignore` entry for a nested
  generated directory, several large files or generated directories
  at once, README name variants, a dependency file outside the root,
  the remaining test-file shapes (`test/` singular, `*_test.py`,
  a non-Python file under `tests/`), a comments-only `.gitignore`,
  a `.gitignore` outside the root, a non-UTF-8 `.py` file, lowercase
  marker words, a marker word inside a longer word, markers in
  `.txt`/`.json` files, `.git` as a generated directory, `.tox` as a
  generated directory, and the `human_size` helper itself.

### Done
- Added `tests/test_check_units.py` (30 tests): direct unit tests for
  every one of the ten check functions, built on hand-made
  `ScanResult` objects with no filesystem at all — each check's happy
  path, finding path and edge cases. Highlights: the empty-directory
  check plus `run_checks` on an empty result reporting exactly the
  six presence findings in check order (and storing them on the
  result); the no-Python-files check asserted as info-level, not a
  warning; the `.gitignore` check naming both missing exclusions;
  the large-file check reporting two files with their sizes; the
  generated-directory check accepting a full-path entry and reporting
  two directories; the syntax check naming file, line and message;
  the reminder-marker check using "1 reminder marker" for one and
  "N reminder markers" for several; the check set asserted in
  reporting order; and direct tests of `human_size` (bytes, KB, MB).
- Added `tests/test_check_edges.py` (18 tests): scanner edge cases
  through temporary directories — a file of exactly 1 MB is not
  flagged (the rule is "over 1 MB"); a bare `README` and a mixed-case
  `Readme.md` both count; a `pyproject.toml` under `src/` does not
  count as the dependency file, and `requirements.txt` is preferred
  over `setup.py`; a `test/` folder and a root `*_test.py` file count
  as tests, while a `.txt` file under `tests/` does not; a
  comments-only `.gitignore` misses both exclusions and a nested
  `.gitignore` does not count; a non-UTF-8 `.py` file is skipped,
  never flagged; a broken file under `src/` is reported by its
  relative path; a lowercase marker word and a marker word inside a
  longer word are not counted, while markers in `.txt` and `.json`
  files are; `.git` is never a generated directory, `.tox` is
  flagged when unlisted, and two generated directories get two
  warnings.
- No check code needed changing: every edge case behaved exactly as
  the checks and the README already described, so no fix was made.
  The new test files contain no literal reminder-marker text, so the
  tool still reports no findings on its own repository.

### Tests / checks run (Day 8)
- `.venv/bin/python -m pytest -q` → **132 passed in 0.84s**
  (84 existing tests + 48 new: 30 direct unit tests in
  `tests/test_check_units.py`, 18 scanner edge-case tests in
  `tests/test_check_edges.py`).
- `.venv/bin/python -m repodoctor .` — exit 0; reported 25 files,
  14 Python files, README yes, Gitignore yes (`.gitignore`),
  Dependency `pyproject.toml`, Test files 7, Large files none,
  Generated dirs `.pytest_cache`, `.venv`,
  `src/repodoctor/__pycache__`, `tests/__pycache__`, Syntax
  errors none, TODO markers none, "Findings: none",
  "Found no findings."
- `.venv/bin/python -m repodoctor . --strict` — exit 0 on the
  clean repo.
- `git diff --check` — clean. No secrets in the tree; `.venv/` is
  ignored. The new tests contain no literal reminder-marker text,
  so the tool still reports no findings on its own repository.

### Commits
- See `git log` for the hashes. Three commits, in plain English.
- Not pushed — the parent pushes to GitHub later.

### Next steps
- Configuration file support, per the plan.

## Day 10 — 2026-11-20 (cross-platform paths and the read-only proof)

### Audit first
- `scanner.py`, `checks.py`, `reporters.py` and `cli.py` were audited
  for platform-specific path handling. What was already right: the
  whole tool uses `pathlib` throughout — no `os.path.join` and no
  string concatenation on paths anywhere in `src/`. What was wrong:
  every path the tool reported was rendered with `str(path)`, which
  gives backslashes on Windows, so text and JSON output would differ
  by platform; `.gitignore` entries written with backslashes (a
  Windows-written file listing `src\__pycache__` or `.venv\`) did
  not match the directories they name; and the skipped-directory
  check split paths on the host platform's separator only, so a
  Windows-style relative path on Linux would arrive as one part and
  be missed.

### Done
- Cross-platform paths, all in code, not just in docs:
  1. Every path the tool reports now uses forward slashes on every
     platform: all `str(path)` renderings in `reporters.py` (text
     summary, JSON document, and the target itself) and every path
     in a finding message in `checks.py` now use
     `Path.as_posix()`. The JSON schema is unchanged
     (`schema_version` stays 1) — only the separator in path
     values changed.
  2. `.gitignore` entries are stored with forward slashes
     (`_normalize_entry` in `scanner.py` turns backslashes into
     forward slashes when the file is read), so a Windows-written
     `.gitignore` matches the same directories as a forward-slash
     one — for the required exclusions, for generated-directory
     coverage, and in the JSON `gitignore_entries` list. The
     matcher in `checks.py` normalises entries the same way, so
     hand-built results with backslash entries match too.
  3. The skipped/generated-directory logic works with either
     separator: a new `_path_parts` helper in `scanner.py` splits
     a path on both `/` and `\`, and `_is_skipped` and the
     test-file folder check use it. The syntax-error file name
     passed to `compile()` is forward-slash form too, and the
     "target does not exist" / "not a directory" errors print the
     target the same way.
- Read-only proof, strengthened with a dedicated module
  (`tests/test_readonly.py`, 5 tests): the scanner's code was
  re-audited — it only calls `rglob`, `stat`, `is_dir`, `is_file`
  and `read_text`, and `compile()` on source text never writes
  bytecode the way importing a module would — and the tests now
  prove it: a scan leaves a folder byte-identical (names,
  contents and modification times, with no new file appearing);
  scanning a folder with a broken Python file creates no `.pyc`
  file and no `__pycache__` directory; no file in the tree gets a
  newer modification time; and a scan of a read-only directory
  (files `0o444`, directories `0o555`) still succeeds, still
  reports its findings, and still creates nothing.
- Updated the README with the forward-slash guarantee and the new
  test modules, with no day numbers. The new test files contain
  no literal reminder-marker text, so the tool still reports no
  findings on its own repository.

### Tests / checks run (Day 10)
- `.venv/bin/python -m pytest -q` → **160 passed in 6.72s**
  (146 existing tests + 14 new: 9 in
  `tests/test_cross_platform.py` — path parts split on either
  separator, skipped directories recognised with backslashes,
  `.gitignore` entries stored with forward slashes, backslash
  exclusions counting as present, a backslash entry covering a
  generated directory, an end-to-end scan honouring backslash
  `.gitignore` entries, and the text report, JSON report and
  finding messages all using forward slashes for Windows-style
  paths built with `PureWindowsPath` — and 5 in
  `tests/test_readonly.py` — the folder byte-identical after a
  scan, no bytecode from a broken file, no modification time
  changed, and a read-only directory scanned successfully with
  nothing created).
- `.venv/bin/python -m repodoctor .` — exit 0; reported 28 files,
  17 Python files, README yes, Gitignore yes (`.gitignore`),
  Dependency `pyproject.toml`, Test files 10, Large files none,
  Generated dirs `.pytest_cache`, `.venv`,
  `src/repodoctor/__pycache__`, `tests/__pycache__`, Syntax
  errors none, TODO markers none, "Findings: none",
  "Found no findings."
- `.venv/bin/python -m repodoctor . --strict` — exit 0 on the
  clean repo.
- `.venv/bin/python -m repodoctor . --format json` — valid JSON,
  exit 0, `schema_version` 1, `findings: []`.
- `git diff --check` — clean. No secrets in the tree; `.venv/` is
  ignored. The new tests contain no literal reminder-marker
  text, so the tool still reports no findings on its own
  repository.

### Commits
- See `git log` for the hashes. Three commits, in plain English.
- Not pushed — the parent pushes to GitHub later.

### Next steps
- Configuration file support, per the plan.
