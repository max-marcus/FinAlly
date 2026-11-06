#!/usr/bin/env bash
# Start FinAlly in Docker. Usage: start_mac.sh [--build] [--open]
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=finally; IMAGE=finally; VOLUME=finally-data; URL=http://localhost:8000
BUILD=0; OPEN=0
for a in "$@"; do case "$a" in --build) BUILD=1;; --open) OPEN=1;; esac; done

if [ "$BUILD" = 1 ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  docker build -t "$IMAGE" .
fi
docker rm -f "$NAME" >/dev/null 2>&1 || true
ENV_ARGS=()
[ -f .env ] && ENV_ARGS=(--env-file .env)
docker run -d --name "$NAME" -p 8000:8000 -v "$VOLUME":/app/db "${ENV_ARGS[@]}" "$IMAGE" >/dev/null
echo "FinAlly running at $URL"
if [ "$OPEN" = 1 ]; then
  (open "$URL" 2>/dev/null || xdg-open "$URL" 2>/dev/null || true)
fi
