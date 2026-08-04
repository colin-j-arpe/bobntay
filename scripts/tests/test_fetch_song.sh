#!/usr/bin/env bash
# test_fetch_song.sh
#
# Exercises scripts/fetch_song.sh against stub_parse_api.py. Covers the retry
# and exit-code matrix, which the Django test suite cannot reach: the script is
# the only thing that decides whether a rejected candidate ends the cron cycle
# or moves on to the next one.
#
# Requires bash, curl, jq and python3. Touches no network, no database and no
# real server. Run it directly:
#
#   scripts/tests/test_fetch_song.sh
#
# Exits 0 if every scenario passes, 1 otherwise.

set -uo pipefail

TEST_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FETCH_SCRIPT="$(dirname "$TEST_DIR")/fetch_song.sh"
STUB="${TEST_DIR}/stub_parse_api.py"

SANDBOX=$(mktemp -d)
trap 'rm -rf "$SANDBOX"' EXIT

FAILURES=0
SCENARIO_OUTPUT=""
SCENARIO_EXIT=0

# fetch_song.sh sources ~/.config/bobntay/.env in preference to the project
# .env, so a fake HOME is what points it at the stub without touching either
# real config file.
setup_fake_home() {
    local port="$1"
    mkdir -p "${SANDBOX}/home/.config/bobntay"
    cat > "${SANDBOX}/home/.config/bobntay/.env" <<EOF
SERVER_URL=http://localhost:${port}
PARSE_API_KEY=stub-key
EOF
}

# run_script <stub env assignments...> — start the stub, run fetch_song.sh
# against it, and leave the result in SCENARIO_OUTPUT / SCENARIO_EXIT.
run_script() {
    local port_file="${SANDBOX}/port"
    rm -f "$port_file"

    PORT_FILE="$port_file" "$@" python3 "$STUB" &
    local stub_pid=$!

    local port=""
    for _ in $(seq 1 100); do
        if [ -s "$port_file" ]; then
            port=$(cat "$port_file")
            break
        fi
        sleep 0.1
    done

    if [ -z "$port" ]; then
        kill "$stub_pid" 2>/dev/null
        echo "stub server failed to start"
        return 1
    fi

    setup_fake_home "$port"
    SCENARIO_OUTPUT=$(HOME="${SANDBOX}/home" bash "$FETCH_SCRIPT" 2>&1)
    SCENARIO_EXIT=$?

    kill "$stub_pid" 2>/dev/null
    wait "$stub_pid" 2>/dev/null
}

fail() {
    echo "  FAIL: $1"
    echo "$SCENARIO_OUTPUT" | sed 's/^/    | /'
    FAILURES=$((FAILURES + 1))
}

expect_exit() {
    [ "$SCENARIO_EXIT" -eq "$1" ] || fail "expected exit $1, got ${SCENARIO_EXIT}"
}

expect_output() {
    grep -q -- "$1" <<< "$SCENARIO_OUTPUT" || fail "expected output matching: $1"
}

expect_no_output() {
    grep -q -- "$1" <<< "$SCENARIO_OUTPUT" && fail "unexpected output matching: $1"
}

expect_count() {
    local actual
    actual=$(grep -c -- "$1" <<< "$SCENARIO_OUTPUT")
    [ "$actual" -eq "$2" ] || fail "expected $2 lines matching '$1', got ${actual}"
}

# ---------------------------------------------------------------------------

echo "A successful submit finishes in one attempt"
run_script env SUBMIT_CODES=200
expect_exit 0
expect_output "Done: Saved"
expect_count "Requesting next song" 1

echo "A 422 moves on to the next candidate instead of aborting"
run_script env SUBMIT_CODES=422,200
expect_exit 0
expect_output "Rejected by server: Tagged Non-Music."
expect_output "Done: Saved"
expect_count "Requesting next song" 2

echo "Unbroken rejections stop at the attempt cap, and that is not an error"
run_script env SUBMIT_CODES=422
expect_exit 0
expect_output "Stopping after 5 attempts"
expect_count "Requesting next song" 5
expect_no_output "Done: Saved"

echo "A 422 whose body is not JSON still logs something usable"
run_script env SUBMIT_CODES=422,200 SUBMIT_BODY=html
expect_exit 0
expect_output "Rejected by server: .*Gateway Error"
expect_output "Done: Saved"

echo "An empty queue is a clean exit, not a retry"
run_script env NEXT_CODES=404
expect_exit 0
expect_output "No new songs to process."
expect_count "Requesting next song" 1

echo "A server error on next-song still fails loudly"
run_script env NEXT_CODES=500
expect_exit 1
expect_output "ERROR: /parse/next-song/ returned status 500"

echo "A server error on submit still fails loudly rather than retrying"
run_script env SUBMIT_CODES=500
expect_exit 1
expect_output "ERROR: /parse/submit-page/ returned status 500"
expect_count "Requesting next song" 1

echo "A blocked Genius fetch still fails loudly"
run_script env PAGE_CODES=403 REPORT_CODES=400
expect_exit 1
expect_output "ERROR: Genius page returned status 403"
expect_output "Server did not record the failure (status 400)"

echo "A deleted Genius page is reported and the next candidate is tried"
run_script env PAGE_CODES=404,200
expect_exit 0
expect_output "Recorded as unavailable: Genius page no longer exists"
expect_output "Done: Saved"
expect_count "Requesting next song" 2

echo "Unbroken deleted pages stop at the attempt cap, and that is not an error"
run_script env PAGE_CODES=404
expect_exit 0
expect_output "Stopping after 5 attempts"
expect_count "Requesting next song" 5
expect_no_output "Done: Saved"

echo "A server without the report endpoint fails exactly as it did before"
run_script env PAGE_CODES=404 REPORT_CODES=404
expect_exit 1
expect_output "ERROR: Genius page returned status 404"
expect_count "Requesting next song" 1

# ---------------------------------------------------------------------------

if [ "$FAILURES" -gt 0 ]; then
    echo
    echo "${FAILURES} assertion(s) failed."
    exit 1
fi

echo
echo "All scenarios passed."
