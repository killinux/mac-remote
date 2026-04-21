#!/bin/sh
# Run on this box. First run generates .env with a fresh TOKEN.
set -eu
cd "$(dirname "$0")"

if [ ! -f .env ]; then
    TOKEN=$(openssl rand -hex 32)
    printf 'TOKEN=%s\n' "$TOKEN" > .env
    chmod 600 .env
    echo "generated .env with new TOKEN:"
    echo "  $TOKEN"
    echo "copy this value to your Mac (set as TOKEN env var)."
fi

. ./.env
export TOKEN

HOST=${HOST:-0.0.0.0}
PORT=${PORT:-8090}
echo "starting mac_server on $HOST:$PORT"

if [ -n "${LOG_FILE:-}" ]; then
    echo "logging to $LOG_FILE (tail -f to follow)"
    exec python3 -u mac_server.py "$HOST" "$PORT" >> "$LOG_FILE" 2>&1
else
    exec python3 mac_server.py "$HOST" "$PORT"
fi
