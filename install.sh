#!/usr/bin/env bash
# Skillhub — one-line install entry:
#   curl -fsSL https://raw.githubusercontent.com/hcodestack/skillhub/main/install.sh | bash
# Clones the repo (if needed) and hands off to the interactive setup wizard.
set -e

REPO_URL="https://github.com/hcodestack/skillhub.git"
DEST="${1:-$HOME/skillhub}"

if [ -f "./setup.sh" ] && [ -d "./server" ]; then
  : # already inside a checkout
else
  command -v git >/dev/null 2>&1 || { echo "git is required — install it first"; exit 1; }
  if [ -d "$DEST/server" ]; then
    echo "Existing install found at $DEST"
  else
    echo "Cloning Skillhub to $DEST ..."
    git clone --depth 1 "$REPO_URL" "$DEST"
  fi
  cd "$DEST"
fi

# stdin is a pipe under curl|bash — give the wizard the real terminal
exec bash ./setup.sh < /dev/tty
