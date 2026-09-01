#!/usr/bin/env bash
# Optional near-real-time push: run the reporter (incremental, subsecond) after
# each Claude Code turn. Register in ~/.claude/settings.json:
#   "hooks": { "Stop": [ { "hooks": [ { "type": "command",
#     "command": "<repo>/reporter/claude-stop-hook.sh" } ] } ] }
DIR="$(cd "$(dirname "$0")" && pwd)"
nohup /usr/bin/python3 "$DIR/skillhub_report.py" \
  --server "${SKILLHUB_SERVER:-http://127.0.0.1:8787}" >/dev/null 2>&1 &
exit 0
