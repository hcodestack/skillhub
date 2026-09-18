#!/usr/bin/env bash
# Install the Skillmgmnt reporter as a cron job (Linux; macOS users can use
# install-launchd.sh instead).
#   ./install-cron.sh [server-url]     default: http://127.0.0.1:8787
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
SERVER="${1:-http://127.0.0.1:8787}"

# run from a stable copy under $HOME so the checkout can move or unmount
INSTALL_DIR="$HOME/.local/lib/skillhub-reporter"
mkdir -p "$INSTALL_DIR"
cp -R "$DIR/skillhub_report.py" "$DIR/adapters" "$INSTALL_DIR/"

LINE="*/15 * * * * /usr/bin/env python3 $INSTALL_DIR/skillhub_report.py --server $SERVER >> /tmp/skillhub-reporter.log 2>&1"
( crontab -l 2>/dev/null | grep -v 'skillhub_report.py' ; echo "$LINE" ) | crontab -
echo "installed cron entry (every 15 min → $SERVER); log: /tmp/skillhub-reporter.log"
echo "first full backfill now:"
python3 "$INSTALL_DIR/skillhub_report.py" --backfill --server "$SERVER" || true
