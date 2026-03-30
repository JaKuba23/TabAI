#!/usr/bin/env bash
# Loads backend/.env and creates or updates Modal secret "tabai-secrets"
# for workers/transcription.py. Run after: modal token new
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env ]]; then
  echo "Missing $ROOT/.env"
  exit 1
fi

set -a
# shellcheck disable=SC1091
source .env
set +a

modal secret delete tabai-secrets --allow-missing --yes 2>/dev/null || true

EXTRA=()
if [[ -n "${DATABASE_SSL_INSECURE:-}" ]]; then
  EXTRA+=(DATABASE_SSL_INSECURE="$DATABASE_SSL_INSECURE")
fi

modal secret create tabai-secrets \
  DATABASE_URL="$DATABASE_URL" \
  R2_ACCOUNT_ID="$R2_ACCOUNT_ID" \
  R2_ACCESS_KEY_ID="$R2_ACCESS_KEY_ID" \
  R2_SECRET_ACCESS_KEY="$R2_SECRET_ACCESS_KEY" \
  R2_BUCKET_NAME="$R2_BUCKET_NAME" \
  "${EXTRA[@]}"

echo "Done. Verify: modal secret list"
