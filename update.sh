#!/usr/bin/env bash
# Skillmgmnt — update to the latest version.
#   ./update.sh            pull + rebuild web if it changed
#   ./update.sh --check    show whether an update is available, change nothing
# User data is never touched: the database lives outside the repo (or under
# server/data/, which is gitignored), and your config is ~/.skillhub/env.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

git fetch -q origin
LOCAL="$(git rev-parse HEAD)"; REMOTE="$(git rev-parse @{u} 2>/dev/null || echo "$LOCAL")"
if [ "$LOCAL" = "$REMOTE" ]; then echo "already up to date ($(git rev-parse --short HEAD))"; exit 0; fi
if [ "${1:-}" = "--check" ]; then
  echo "update available: $(git rev-parse --short HEAD) → $(git rev-parse --short @{u})"
  git log --oneline HEAD..@{u} | head -10
  exit 0
fi

WEB_BEFORE="$(git rev-parse HEAD:web 2>/dev/null || echo none)"
git pull --ff-only
WEB_AFTER="$(git rev-parse HEAD:web 2>/dev/null || echo none)"

( cd server && command -v uv >/dev/null && uv sync -q ) || true
if [ "$WEB_BEFORE" != "$WEB_AFTER" ]; then
  if command -v pnpm >/dev/null 2>&1; then
    echo "web changed — rebuilding UI …"
    ( cd web && pnpm install --silent && pnpm build >/dev/null )
  else
    echo "web changed but pnpm is missing — UI stays on the old build until you run: cd web && pnpm build"
  fi
fi
echo "updated to $(git rev-parse --short HEAD) — restart with: skillhub stop && skillhub"
