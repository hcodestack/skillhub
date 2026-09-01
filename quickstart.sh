#!/usr/bin/env bash
# One-command local Skillhub: build (first run only), start, self-report.
#
#   ./quickstart.sh /path/to/your/skills-library
#   ./quickstart.sh                # uses the bundled demo library
#
# Needs: Python 3.11+ with `uv` (https://docs.astral.sh/uv), Node with `pnpm`
# (first run only, to build the web UI once). Everything stays on 127.0.0.1.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
LIB="${1:-$DIR/examples/demo-library}"

command -v uv >/dev/null || { echo "需要 uv：https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }
[ -d "$LIB" ] || { echo "技能库目录不存在: $LIB"; exit 1; }

if [ ! -f "$DIR/web/dist/index.html" ]; then
  command -v pnpm >/dev/null || { echo "首次运行需要 pnpm 构建前端一次：npm i -g pnpm"; exit 1; }
  echo "▸ 首次运行：构建前端（之后不再需要）…"
  (cd "$DIR/web" && pnpm install --silent && pnpm build)
fi

echo "▸ 同步 Python 依赖…"
(cd "$DIR/server" && uv sync -q)

echo "▸ 启动 Skillhub"
echo "  库:      $LIB"
echo "  看板:    http://127.0.0.1:${SKILLHUB_PORT:-8787}"
echo "  MCP:     claude mcp add skillhub -- \"$DIR/mcp/skillhub_mcp.py\" http://127.0.0.1:${SKILLHUB_PORT:-8787}"
echo "  （本机库存与调用记录由内置自上报维护，每 15 分钟一次；首轮含历史回填）"
echo
cd "$DIR/server"
exec env SKILLHUB_LIBRARY_ROOT="$LIB" uv run skillhub-server
