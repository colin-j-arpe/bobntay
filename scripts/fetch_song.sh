#!/usr/bin/env bash
# fetch_song.sh
#
# Fetches the next unprocessed song from the remote server, downloads the
# Genius lyrics page from the local machine (bypassing server-side bot
# detection), and submits the HTML back to the server for parsing and storage.
#
# If the server rejects a candidate on the strength of its HTML (422), or the
# Genius page turns out to be gone, the whole cycle is retried with the next
# candidate, up to MAX_ATTEMPTS times.
#
# Configuration is loaded from the first .env file found in this order:
#   1. ~/.config/bobntay/.env  (user-level override, keeps secrets out of the repo)
#   2. <repo-root>/.env        (project .env, suitable for local Docker installs)
#
# The file must contain:
#   SERVER_URL     - Base URL of the app, e.g. https://bobntay.example.com
#                    or http://localhost:8000 for a local Docker instance
#   PARSE_API_KEY  - Secret key matching PARSE_API_KEY in the app's environment
#
# Suggested cron entry (runs hourly, logs to file):
#   0 * * * * /path/to/repo/scripts/fetch_song.sh \
#     >> ~/.local/logs/bobntay_fetch.log 2>&1

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

USER_CONFIG="${HOME}/.config/bobntay/.env"
PROJECT_ENV="${REPO_ROOT}/.env"

if [ -f "$USER_CONFIG" ]; then
    # shellcheck source=/dev/null
    source "$USER_CONFIG"
elif [ -f "$PROJECT_ENV" ]; then
    # shellcheck source=/dev/null
    source "$PROJECT_ENV"
fi

SERVER_URL="${SERVER_URL:?SERVER_URL not set. Add it to ${USER_CONFIG} or ${PROJECT_ENV}}"
PARSE_API_KEY="${PARSE_API_KEY:?PARSE_API_KEY not set. Add it to ${USER_CONFIG} or ${PROJECT_ENV}}"

WORK_DIR=$(mktemp -d)
trap 'rm -rf "$WORK_DIR"' EXIT

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"
}

# Pull the human-readable message out of a JSON response body, falling back to
# the raw body when the response was not JSON at all — a proxy error page, say.
response_detail() {
    jq -r '.detail // empty' "$1" 2>/dev/null || cat "$1"
}

# Tell the server the Genius page could not be fetched. Only this machine ever sees
# that failure, and a page that has been deleted is a permanent property of the
# track — unreported, it stalls every future run on the same candidate.
#
# The observed status is reported and nothing else: the server decides which
# statuses are a verdict about the track (a deleted page) and which are about this
# machine (bot detection, an outage). Returns 0 only when a rejection was recorded,
# so an older server without the endpoint simply fails the way it always did.
report_page_failure() {
    local status="$1"
    local body="${WORK_DIR}/page_failure.json"
    local response="${WORK_DIR}/page_failure_response.json"

    jq --argjson status "$status" '{track_data: .track, page_status: $status}' \
        "${WORK_DIR}/next_song.json" \
        > "$body"

    local code
    code=$(curl -s \
        -o "$response" \
        -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-Api-Key: ${PARSE_API_KEY}" \
        -d "@${body}" \
        "${SERVER_URL}/parse/report-page-failure/")

    if [ "$code" -eq 200 ]; then
        log "Recorded as unavailable: $(response_detail "$response")"
        return 0
    fi

    log "Server did not record the failure (status ${code}): $(response_detail "$response")"
    return 1
}

# The server only discovers some bad candidates once it has seen the page HTML:
# a Non-Music page, or one with no lyrics on it. It answers those with 422 and
# records the rejection, so simply asking again yields a different track. Retry
# rather than abort, but cap the attempts so a run of consecutive rejections
# cannot turn one cron cycle into an unbounded crawl.
MAX_ATTEMPTS=5

for ((ATTEMPT = 1; ATTEMPT <= MAX_ATTEMPTS; ATTEMPT++)); do
    # -----------------------------------------------------------------------
    # Step 1: Ask the server for the next unprocessed song
    # -----------------------------------------------------------------------
    log "Requesting next song from server (attempt ${ATTEMPT} of ${MAX_ATTEMPTS})..."

    HTTP_CODE=$(curl -s \
        -o "${WORK_DIR}/next_song.json" \
        -w "%{http_code}" \
        -H "X-Api-Key: ${PARSE_API_KEY}" \
        "${SERVER_URL}/parse/next-song/")

    if [ "$HTTP_CODE" -eq 404 ]; then
        log "No new songs to process."
        exit 0
    fi

    if [ "$HTTP_CODE" -ne 200 ]; then
        log "ERROR: /parse/next-song/ returned status ${HTTP_CODE}: $(cat "${WORK_DIR}/next_song.json")"
        exit 1
    fi

    GENIUS_URL=$(jq -r '.track.url' "${WORK_DIR}/next_song.json")
    SONG_TITLE=$(jq -r '.track.title' "${WORK_DIR}/next_song.json")
    SONG_ARTIST=$(jq -r '.track.primary_artist_names' "${WORK_DIR}/next_song.json")

    log "Found: \"${SONG_TITLE}\" by ${SONG_ARTIST}"

    # -----------------------------------------------------------------------
    # Step 2: Fetch the Genius lyrics page from this machine
    # -----------------------------------------------------------------------
    log "Fetching Genius page: ${GENIUS_URL}"

    HTTP_CODE=$(curl -s \
        -o "${WORK_DIR}/page.html" \
        -w "%{http_code}" \
        -H 'User-Agent: Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36' \
        "${GENIUS_URL}")

    if [ "$HTTP_CODE" -ne 200 ]; then
        log "Genius page returned status ${HTTP_CODE}; reporting to server..."
        if report_page_failure "$HTTP_CODE"; then
            continue
        fi
        log "ERROR: Genius page returned status ${HTTP_CODE}"
        exit 1
    fi

    HTML_SIZE=$(wc -c < "${WORK_DIR}/page.html")
    log "Fetched ${HTML_SIZE} bytes."

    # -----------------------------------------------------------------------
    # Step 3: Build the JSON request body and submit to the server
    # -----------------------------------------------------------------------
    # jq --rawfile reads the HTML file as a plain string, safely escaping all
    # characters that would otherwise break the JSON payload.
    jq '{track_data: .track, genius_record: .genius_record, html: $html}' \
        --rawfile html "${WORK_DIR}/page.html" \
        "${WORK_DIR}/next_song.json" \
        > "${WORK_DIR}/request.json"

    log "Submitting to server..."

    HTTP_CODE=$(curl -s \
        -o "${WORK_DIR}/submit_response.json" \
        -w "%{http_code}" \
        -X POST \
        -H "Content-Type: application/json" \
        -H "X-Api-Key: ${PARSE_API_KEY}" \
        -d "@${WORK_DIR}/request.json" \
        "${SERVER_URL}/parse/submit-page/")

    if [ "$HTTP_CODE" -eq 422 ]; then
        log "Rejected by server: $(response_detail "${WORK_DIR}/submit_response.json")"
        continue
    fi

    if [ "$HTTP_CODE" -ne 200 ]; then
        log "ERROR: /parse/submit-page/ returned status ${HTTP_CODE}: $(cat "${WORK_DIR}/submit_response.json")"
        exit 1
    fi

    log "Done: $(jq -r '.detail' "${WORK_DIR}/submit_response.json")"
    exit 0
done

# Not an error: each rejection was recorded server-side, so the next cron cycle
# starts from a shorter queue of bad candidates rather than repeating this one.
log "Stopping after ${MAX_ATTEMPTS} attempts; every candidate was rejected."
exit 0
