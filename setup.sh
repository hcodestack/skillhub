#!/usr/bin/env bash
# Skillmgmnt setup — guided install for the single-machine (local) mode.
#
#   ./setup.sh                     interactive wizard (default)
#   ./setup.sh --non-interactive --library /path/to/skills-library [...]
#
# What it does: checks prerequisites, shows which AI coding tools it detected
# on this machine, asks where your skills library is, builds the web UI once,
# installs the `skillhub` command, and (optionally) registers the hub as an
# MCP tool in Claude Code and sets up start-at-login.
#
# Non-interactive options (what an AI agent typically runs — agents:
# read AGENTS.md for the full runbook, including verification steps):
#   ./setup.sh --non-interactive --library ~/skills --connect-mcp auto --lang en
#
#   --non-interactive, -y     no prompts; requires --library
#   --library <path>          your skills library (dirs containing SKILL.md)
#   --port <n>                dashboard port                   (default: 8787)
#   --connect-mcp <mode>      auto | claude | none             (default: auto)
#                             auto = register with Claude Code if its CLI exists
#   --autostart <0|1>         start at login via launchd (macOS only) (default: 0)
#   --start <0|1>             start the server when setup finishes    (default: 1)
#   --lang <en|zh>            wizard language                  (default: from $LANG)
#   --force                   re-run even if already configured
set -u

DIR="$(cd "$(dirname "$0")" && pwd)"
CONF_DIR="$HOME/.skillhub"
ENV_FILE="$CONF_DIR/env"

BOLD='\033[1m'; DIM='\033[2m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'
RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'

NON_INTERACTIVE=0; LIB=""; PORT=8787; CONNECT_MCP="auto"; AUTOSTART=0
START_AFTER=1; FORCE=0
case "${LANG:-en}" in zh*|*zh_CN*) UI=zh ;; *) UI=en ;; esac

t() { if [ "$UI" = zh ]; then printf '%s' "$2"; else printf '%s' "$1"; fi; }
say()  { printf '%b\n' "$*"; }
ok()   { say "  ${GREEN}✓${NC} $*"; }
warn() { say "  ${YELLOW}!${NC} $*"; }
die()  { say "  ${RED}✗${NC} $*"; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --non-interactive|-y) NON_INTERACTIVE=1 ;;
    --library)     LIB="$2"; shift ;;
    --port)        PORT="$2"; shift ;;
    --connect-mcp) CONNECT_MCP="$2"; shift ;;
    --autostart)   AUTOSTART="$2"; shift ;;
    --start)       START_AFTER="$2"; shift ;;
    --lang)        UI="$2"; shift ;;
    --force)       FORCE=1 ;;
    --help|-h)     sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) die "unknown option: $1 (see ./setup.sh --help)" ;;
  esac
  shift
done

# ── already configured? ──────────────────────────────────────────────────────
if [ -f "$ENV_FILE" ] && [ "$FORCE" -eq 0 ] && [ "$NON_INTERACTIVE" -eq 1 ]; then
  say "$(t "Already configured ($ENV_FILE). Use --force to redo." \
           "已配置过（$ENV_FILE）。用 --force 重新配置。")"
  exit 0
fi

say ""
say "  ${BOLD}Skillmgmnt${NC} ${DIM}$(t "— setup" "— 安装向导")${NC}"
say "  ${DIM}──────────────────────────────────────────────${NC}"

# ── [1/5] prerequisites ─────────────────────────────────────────────────────
say ""
say "  ${DIM}[1/5]${NC} ${CYAN}$(t "Prerequisites" "环境检查")${NC}"
PY="$(command -v python3 || true)"
[ -n "$PY" ] || die "$(t "python3 not found — install Python 3.11+" \
                        "未找到 python3——请安装 Python 3.11+")"
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' \
  || die "$(t "Python 3.11+ required" "需要 Python 3.11+")"
ok "python3 $("$PY" -V 2>&1 | cut -d' ' -f2)"

if command -v uv >/dev/null 2>&1; then
  ok "uv"
else
  die "$(t "uv not found — install: https://docs.astral.sh/uv/getting-started/installation/" \
           "未找到 uv——安装见 https://docs.astral.sh/uv/getting-started/installation/")"
fi

NEED_BUILD=0
if [ ! -f "$DIR/web/dist/index.html" ]; then
  NEED_BUILD=1
  if command -v pnpm >/dev/null 2>&1; then
    ok "pnpm $(t "(web UI will be built once)" "（首次将构建一次前端）")"
  else
    warn "$(t "pnpm not found — the API will work but the dashboard UI can't be built. Install: npm i -g pnpm, then re-run." \
              "未找到 pnpm——API 可用但看板界面无法构建。安装：npm i -g pnpm 后重跑。")"
  fi
fi

# ── [2/5] detect this machine's AI tools (our own 47-entry table) ───────────
say ""
say "  ${DIM}[2/5]${NC} ${CYAN}$(t "AI tools on this machine" "本机的 AI 工具")${NC}"
say "  ${DIM}$(t "Skillmgmnt will watch skills across all of these:" \
                 "Skillmgmnt 将观测以下工具的技能目录：")${NC}"
DETECTED="$(cd "$DIR/reporter" && "$PY" -c '
import sys; sys.path.insert(0, ".")
from adapters.tools import installed_tools
from adapters.tool_table import TOOLS, NAME
for k in installed_tools():
    print(TOOLS[k][NAME])
' 2>/dev/null || true)"
if [ -n "$DETECTED" ]; then
  echo "$DETECTED" | while IFS= read -r name; do ok "$name"; done
  N_TOOLS="$(echo "$DETECTED" | wc -l | tr -d ' ')"
else
  N_TOOLS=0
  warn "$(t "none detected yet — the dashboard fills in as tools appear" \
            "暂未检测到——装了工具后看板会自动出现")"
fi

# ── [3/5] where is the skills library? ──────────────────────────────────────
say ""
say "  ${DIM}[3/5]${NC} ${CYAN}$(t "Your skills library" "你的技能库")${NC}"
DEMO="$DIR/examples/demo-library"
if [ "$NON_INTERACTIVE" -eq 1 ]; then
  [ -n "$LIB" ] || die "$(t "--non-interactive requires --library" \
                           "--non-interactive 需要同时给 --library")"
else
  if [ -z "$LIB" ]; then
    say "  ${DIM}$(t "Any directory tree whose folders contain SKILL.md files." \
                     "任何包含 SKILL.md 目录的目录树都可以。")${NC}"
    printf "  $(t "Library path (empty = bundled demo library): " \
                  "库路径（留空 = 使用自带演示库）: ")"
    read -r LIB </dev/tty || LIB=""
    [ -n "$LIB" ] || LIB="$DEMO"
  fi
fi
LIB="${LIB/#\~/$HOME}"
LIB="$(cd "$LIB" 2>/dev/null && pwd)" || die "$(t "directory not found" "目录不存在")"
N_SKILLS="$(find "$LIB" -maxdepth 5 -name 'SKILL.md' 2>/dev/null | head -500 | wc -l | tr -d ' ')"
if [ "$N_SKILLS" -eq 0 ]; then
  warn "$(t "no SKILL.md found under $LIB — the catalog will be empty until skills appear" \
            "$LIB 下没有找到 SKILL.md——放入技能前目录页会是空的")"
else
  ok "$LIB  ${DIM}($N_SKILLS SKILL.md)${NC}"
fi

# ── [4/5] install: deps, web build, config, launcher ────────────────────────
say ""
say "  ${DIM}[4/5]${NC} ${CYAN}$(t "Install" "安装")${NC}"
( cd "$DIR/server" && uv sync -q ) || die "uv sync failed"
ok "$(t "Python dependencies" "Python 依赖")"

if [ "$NEED_BUILD" -eq 1 ] && command -v pnpm >/dev/null 2>&1; then
  ( cd "$DIR/web" && pnpm install --silent && pnpm build >/dev/null 2>&1 ) \
    && ok "$(t "web UI built" "前端已构建")" \
    || warn "$(t "web build failed — API still works; see web/ to retry" \
                 "前端构建失败——API 仍可用；到 web/ 手动重试")"
fi

mkdir -p "$CONF_DIR"
cat > "$ENV_FILE" <<EOF
# Skillmgmnt local config — sourced by bin/skillhub and launchd. Edit freely.
SKILLMGMNT_REPO="$DIR"
SKILLMGMNT_LIBRARY_ROOT="$LIB"
SKILLMGMNT_PORT=$PORT
EOF
ok "$(t "config written:" "配置已写入：") ${DIM}$ENV_FILE${NC}"

BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"
chmod +x "$DIR/bin/skillhub"
ln -sf "$DIR/bin/skillhub" "$BIN_DIR/skillhub"
ok "$(t "'skillhub' command installed" "'skillhub' 命令已安装")"
case ":$PATH:" in
  *":$BIN_DIR:"*) : ;;
  *)
    for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do
      if [ -f "$rc" ] && ! grep -q '# skillhub:path' "$rc" 2>/dev/null; then
        printf '\nexport PATH="$HOME/.local/bin:$PATH" # skillhub:path\n' >> "$rc"
      fi
    done
    warn "$(t "added ~/.local/bin to PATH (new terminals)" \
              "已把 ~/.local/bin 加入 PATH（新终端生效）")"
    ;;
esac

# optional: start at login (macOS launchd)
if [ "$NON_INTERACTIVE" -eq 0 ] && [ "$(uname)" = "Darwin" ]; then
  printf "  $(t "Start Skillmgmnt automatically at login? [y/N] " \
                "开机自动启动 Skillmgmnt？[y/N] ")"
  read -r yn </dev/tty || yn=""
  case "$yn" in y|Y) AUTOSTART=1 ;; esac
fi
if [ "$AUTOSTART" = "1" ] && [ "$(uname)" = "Darwin" ]; then
  PLIST="$HOME/Library/LaunchAgents/com.skillhub.server.plist"
  mkdir -p "$HOME/Library/LaunchAgents"
  sed -e "s|__REPO__|$DIR|g" -e "s|__HOME__|$HOME|g" \
      -e "s|__PORT__|$PORT|g" -e "s|__LIBRARY__|$LIB|g" \
      "$DIR/deploy/com.skillhub.server.plist" > "$PLIST"
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST" 2>/dev/null \
    && ok "$(t "start-at-login enabled (launchd)" "开机自启已启用（launchd）")" \
    || warn "$(t "could not load launchd job — start manually with 'skillhub'" \
                 "launchd 加载失败——用 'skillhub' 手动启动")"
elif [ "$AUTOSTART" = "1" ]; then
  warn "$(t "autostart template for Linux: deploy/skillhub.service (systemd --user)" \
            "Linux 自启模板见 deploy/skillhub.service（systemd --user）")"
fi

# ── [5/5] connect your CLI agent (MCP) ──────────────────────────────────────
say ""
say "  ${DIM}[5/5]${NC} ${CYAN}$(t "Connect your CLI agent (MCP)" "接入你的 CLI agent（MCP）")${NC}"
MCP_DONE=0
HAS_CLAUDE=0; command -v claude >/dev/null 2>&1 && HAS_CLAUDE=1
DO_CLAUDE=0
case "$CONNECT_MCP" in
  auto)   DO_CLAUDE=$HAS_CLAUDE ;;
  claude) DO_CLAUDE=1 ;;
  none)   DO_CLAUDE=0 ;;
  *) die "--connect-mcp must be auto | claude | none" ;;
esac
if [ "$NON_INTERACTIVE" -eq 0 ] && [ "$HAS_CLAUDE" -eq 1 ] && [ "$CONNECT_MCP" = "auto" ]; then
  printf "  $(t "Claude Code detected — register Skillmgmnt as one of its tools? [Y/n] " \
                "检测到 Claude Code——把 Skillmgmnt 注册为它的工具？[Y/n] ")"
  read -r yn </dev/tty || yn=""
  case "$yn" in n|N) DO_CLAUDE=0 ;; *) DO_CLAUDE=1 ;; esac
fi
if [ "$DO_CLAUDE" -eq 1 ] && [ "$HAS_CLAUDE" -eq 1 ]; then
  if claude mcp add skillhub -- "$DIR/mcp/skillhub_mcp.py" "http://127.0.0.1:$PORT" >/dev/null 2>&1; then
    ok "$(t "registered in Claude Code (tool name: skillhub)" \
            "已注册进 Claude Code（工具名 skillhub）")"
    MCP_DONE=1
  else
    warn "$(t "claude mcp add failed — run manually:" "claude mcp add 失败——手动执行：")"
    say "     ${DIM}claude mcp add skillhub -- \"$DIR/mcp/skillhub_mcp.py\" http://127.0.0.1:$PORT${NC}"
  fi
elif [ "$DO_CLAUDE" -eq 1 ]; then
  warn "$(t "claude CLI not found — register later with:" "未找到 claude CLI——之后可手动注册：")"
  say "     ${DIM}claude mcp add skillhub -- \"$DIR/mcp/skillhub_mcp.py\" http://127.0.0.1:$PORT${NC}"
fi
if [ -d "$HOME/.codex" ]; then
  say "  ${DIM}$(t "Codex users — add to ~/.codex/config.toml:" \
                   "Codex 用户——在 ~/.codex/config.toml 加入：")${NC}"
  say "     ${DIM}[mcp_servers.skillhub]${NC}"
  say "     ${DIM}command = \"$DIR/mcp/skillhub_mcp.py\"${NC}"
  say "     ${DIM}args = [\"http://127.0.0.1:$PORT\"]${NC}"
fi

# ── done ────────────────────────────────────────────────────────────────────
say ""
say "  ${DIM}──────────────────────────────────────────────${NC}"
say "  ${GREEN}${BOLD}$(t "Setup complete." "安装完成。")${NC}"
say ""
say "    $(t "dashboard" "看板")     ${BOLD}http://127.0.0.1:$PORT${NC}"
say "    $(t "commands" "常用命令")   ${DIM}skillhub · skillhub stop · skillhub status · skillhub update${NC}"
say "    $(t "library" "技能库")     ${DIM}$LIB${NC}"
[ "$MCP_DONE" -eq 1 ] && \
  say "    MCP          ${DIM}$(t "ask your agent things like: 'which skills does nobody use?'" \
                                  "现在可以直接问你的 agent：「哪些技能没人用？」")${NC}"
say ""
if [ "$START_AFTER" = "1" ]; then
  exec "$DIR/bin/skillhub"
else
  say "  ${DIM}$(t "start any time with: skillhub" "随时用 skillhub 命令启动")${NC}"
fi
