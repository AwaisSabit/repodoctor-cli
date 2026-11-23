#!/bin/sh
# Clean-environment smoke test for RepoDoctor.
#
# Builds a fresh virtual environment, installs RepoDoctor from this
# repository into it, and runs the installed `repodoctor` command
# against a small healthy sample project and a messy one, in text
# and JSON, strict and non-strict. Every step prints PASS or FAIL
# and the script exits non-zero if any step fails, so it works as
# a release check before tagging a version.
#
# Usage: ./scripts/smoke-test.sh [venv-dir]
# The venv defaults to $HOME/.repodoctor-smoke-venv. An existing
# venv at that path is removed first. The venv is removed again
# when the smoke test passes, and kept for inspection when it fails.
#
# The marker word in the messy project is built from pieces so this
# script itself contains no literal marker text — the tool would
# otherwise flag its own repository when scanning it.

set -eu

REPO=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
VENV=${1:-"$HOME/.repodoctor-smoke-venv"}
FAILURES=0

step() {
    # step <name> <expected-exit> <command...>: run the command and
    # report PASS when its exit code is the expected one.
    name=$1
    expected=$2
    shift 2
    set +e
    "$@" > "$VENV/smoke-out.txt" 2>&1
    actual=$?
    set -e
    if [ "$actual" -eq "$expected" ]; then
        echo "PASS: $name (exit $actual)"
    else
        echo "FAIL: $name (expected exit $expected, got $actual)"
        cat "$VENV/smoke-out.txt"
        FAILURES=$((FAILURES + 1))
    fi
}

check_contains() {
    # check_contains <name> <file> <text>: PASS when the file holds
    # the text.
    if grep -qF "$3" "$2"; then
        echo "PASS: $1"
    else
        echo "FAIL: $1 (missing: $3)"
        cat "$2"
        FAILURES=$((FAILURES + 1))
    fi
}

echo "Repository: $REPO"
echo "Venv: $VENV"
rm -rf "$VENV"
python3 -m venv "$VENV"
"$VENV/bin/pip" install -q -e "$REPO"
echo "PASS: installed repodoctor into a fresh venv"

SAMPLE="$VENV/sample-project"
MESSY="$VENV/messy-project"
mkdir -p "$SAMPLE/tests" "$MESSY"
printf '# Sample\n' > "$SAMPLE/README.md"
printf 'VALUE = 1\n' > "$SAMPLE/app.py"
printf '.venv/\n__pycache__/\n' > "$SAMPLE/.gitignore"
printf '[project]\nname = "sample"\n' > "$SAMPLE/pyproject.toml"
printf 'def test_value():\n    assert VALUE == 1\n' > "$SAMPLE/tests/test_app.py"
printf 'def broken(\n' > "$MESSY/broken.py"
printf 'Some notes.\n%s\n' "TO""DO"": finish the notes" > "$MESSY/notes.txt"

BIN="$VENV/bin/repodoctor"
step "version prints the installed version" 0 "$BIN" --version
step "healthy project, text scan exits 0" 0 "$BIN" "$SAMPLE"
check_contains "healthy project reports no findings" \
    "$VENV/smoke-out.txt" "Found no findings."
step "healthy project, JSON scan exits 0" 0 "$BIN" "$SAMPLE" --format json
"$BIN" "$SAMPLE" --format json > "$VENV/smoke-json.txt"
check_contains "JSON summary is all zeros" \
    "$VENV/smoke-json.txt" '"total": 0'
step "healthy project, strict scan exits 0" 0 "$BIN" "$SAMPLE" --strict
step "messy project, text scan exits 0 without strict" 0 "$BIN" "$MESSY"
step "messy project, strict scan exits 1" 1 "$BIN" "$MESSY" --strict
step "messy project, strict JSON scan exits 1" 1 "$BIN" "$MESSY" --strict --format json

if [ "$FAILURES" -eq 0 ]; then
    echo "Smoke test passed: all steps green."
    rm -rf "$VENV"
else
    echo "Smoke test failed: $FAILURES step(s) failed. Venv kept at $VENV."
    exit 1
fi
