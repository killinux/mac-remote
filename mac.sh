#!/bin/sh
# Run on your Mac. Needs .env with TOKEN and SERVER_URL.
set -eu
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    echo "missing .env — create one with:" >&2
    echo "  TOKEN=<same token as server>" >&2
    echo "  SERVER_URL=http://<server-public-ip>:8090" >&2
    exit 1
fi

. ./.env
: "${TOKEN:?TOKEN not set in .env}"
: "${SERVER_URL:?SERVER_URL not set in .env}"
export TOKEN SERVER_URL

echo "starting mac_agent, polling $SERVER_URL"

if [ -n "${LOG_FILE:-}" ]; then
    echo "logging to $LOG_FILE (tail -f to follow)"
    exec python3 -u mac_agent.py >> "$LOG_FILE" 2>&1
else
    exec python3 mac_agent.py
fi
