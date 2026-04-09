#!/usr/bin/env bash
set -euo pipefail

PING_URL="${1:-}"
REPO_DIR="${2:-.}"
DOCKER_BUILD_TIMEOUT="${DOCKER_BUILD_TIMEOUT:-600}"

if [[ -z "$PING_URL" ]]; then
  echo "Usage: $0 <ping_url> [repo_dir]"
  echo "Example: $0 https://my-space.hf.space ."
  exit 1
fi

if [[ ! -d "$REPO_DIR" ]]; then
  echo "Error: repo directory not found: $REPO_DIR"
  exit 1
fi

PING_URL="${PING_URL%/}"

echo "Step 1/3: Pinging Space reset endpoint..."
HTTP_CODE="$(curl -s -o /dev/null -w "%{http_code}" -X POST \
  -H "Content-Type: application/json" -d '{}' "${PING_URL}/reset" || true)"

if [[ "$HTTP_CODE" != "200" ]]; then
  echo "FAILED: ${PING_URL}/reset returned HTTP ${HTTP_CODE} (expected 200)"
  exit 1
fi
echo "PASSED: Space reset endpoint is live"

echo "Step 2/3: Building Docker image..."
if command -v timeout >/dev/null 2>&1; then
  timeout "${DOCKER_BUILD_TIMEOUT}" docker build "$REPO_DIR"
else
  docker build "$REPO_DIR"
fi
echo "PASSED: Docker build succeeded"

echo "Step 3/3: Running openenv validate..."
(cd "$REPO_DIR" && openenv validate)
echo "PASSED: openenv validate succeeded"

echo "All checks passed."
