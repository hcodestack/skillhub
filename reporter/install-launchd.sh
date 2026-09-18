#!/usr/bin/env bash
# Install the Skillmgmnt reporter as a macOS LaunchAgent (runs every 15 min).
#   ./install-launchd.sh [server-url]     default: http://127.0.0.1:8787
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER="${1:-http://127.0.0.1:8787}"
PLIST="$HOME/Library/LaunchAgents/com.skillhub.reporter.plist"

# launchd + macOS TCC: background agents can't read external/network volumes
# without extra grants — install a copy under $HOME and run from there.
INSTALL_DIR="$HOME/.local/lib/skillhub-reporter"
mkdir -p "$INSTALL_DIR" "$HOME/Library/LaunchAgents"
rsync -a --delete --exclude '__pycache__' "$DIR/" "$INSTALL_DIR/"

sed -e "s|__REPORTER_DIR__|$INSTALL_DIR|g" -e "s|__SERVER__|$SERVER|g" \
  "$DIR/launchd/com.skillhub.reporter.plist" > "$PLIST"
launchctl unload "$PLIST" 2>/dev/null || true
launchctl load "$PLIST"
echo "installed: $PLIST (server: $SERVER, every 15 min)"
echo "logs: /tmp/skillhub-reporter.log"
