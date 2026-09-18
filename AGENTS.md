# Skillmgmnt — Agent Runbook

You are an AI coding agent (Claude Code, Codex, or similar) and a user has
asked you to install, operate, or troubleshoot Skillmgmnt for them. This file is
written for you. Converse with the user in **their** language; run the
commands exactly as given. Prefer the non-interactive paths below over the
interactive wizard — you are the wizard.

Skillmgmnt is a read-only dashboard of the AI-agent skills on this machine:
what exists in the user's skills library, which of 47+ tools load each skill,
what gets used, and what is broken. Nothing here modifies the user's skills.

## Install (single machine — the default)

### 0. Where am I?

If you are not already inside a Skillmgmnt checkout (`setup.sh` and `server/`
present), clone first — ask the user where, defaulting to `~/skillhub`:

```bash
git clone https://github.com/hcodestack/skillmgmnt.git ~/skillhub && cd ~/skillhub
```

### 1. Preflight — check, don't assume

```bash
python3 -c 'import sys; print(sys.version_info >= (3,11))'   # must print True
command -v uv || echo MISSING-uv
command -v pnpm || echo MISSING-pnpm
```

- `uv` missing → it installs with
  `curl -LsSf https://astral.sh/uv/install.sh | sh` — **ask the user before
  installing anything**, then re-check.
- `pnpm` missing → the dashboard UI cannot be built; the API still works.
  Offer `npm i -g pnpm` if Node exists, otherwise continue and say the UI
  will be available after they install pnpm and re-run setup.

### 2. Find the user's skills library

The library is any directory tree whose folders contain `SKILL.md` files.
Ask the user if they know where it is. If they don't, help them look —
cluster SKILL.md files by parent directory and present the candidates:

```bash
find "$HOME" -maxdepth 6 -name SKILL.md -not -path '*/node_modules/*' \
  -not -path '*/.git/*' 2>/dev/null | sed 's|/[^/]*/SKILL.md$||' | sort | uniq -c | sort -rn | head
```

Interpretation for the user: a directory with many hits *that they curate
themselves* is likely their library. Three kinds of high-scoring hits are
NOT it: tool entry points (`~/.claude/skills`-style), marketplace/plugin
caches (paths containing `marketplace`, `cache`, `Downloads`), and backup
folders. If the user keeps the library outside `$HOME` (an external volume,
a NAS mount), repeat the find against that mount point — e.g.
`find /Volumes/<name> -maxdepth 5 -name SKILL.md … `. No library at all is fine:
offer the bundled demo (`examples/demo-library`) so they can see the product,
and tell them the catalog page fills in once a real library exists.

### 3. Run setup non-interactively

```bash
./setup.sh --non-interactive \
  --library "<PATH-FROM-STEP-2>" \
  --connect-mcp auto \
  --start 0
```

Flags you may add after asking the user:
`--port <n>` (default 8787) · `--autostart 1` (macOS start-at-login) ·
`--lang zh` (wizard/log language — the dashboard itself opens in English and
has its own `EN | 中文` switch in the header, so this flag is only about the
installer's output).

`--connect-mcp auto` registers the hub as an MCP tool in Claude Code when the
`claude` CLI is present — that MCP server is how **you** will query Skillmgmnt
afterwards, so keep it unless the user objects. If you are Codex, also append
to `~/.codex/config.toml` (with the user's consent), substituting the real
checkout path:

```toml
[mcp_servers.skillhub]
command = "<CHECKOUT>/mcp/skillhub_mcp.py"
args = ["http://127.0.0.1:8787"]
```

### 4. Start and verify — prove it, don't declare it

```bash
export PATH="$HOME/.local/bin:$PATH"
SKILLMGMNT_NO_OPEN=1 skillhub          # start in background, skip browser
skillhub status                       # expect: running (pid …)
curl -s http://127.0.0.1:8787/api/v1/library/status   # expect: {"count": N>0, …}
curl -s http://127.0.0.1:8787/api/v1/stats/tiles      # expect JSON tiles
```

The server's built-in self-reporter scans this machine's AI tools ~10 seconds
after start (first run also backfills usage history; with many session logs
that can take a minute). Verify it landed:

```bash
sleep 75 && curl -s http://127.0.0.1:8787/api/v1/stats/tiles
# "tools" and "loaded_skills" should now be non-zero on a machine with AI tools
```

Then tell the user the dashboard is at `http://127.0.0.1:8787` and offer to
open it. Report what the tiles say — that first number is the product.

### 5. If something failed

| Symptom | Fix |
|---|---|
| `skillhub: not set up yet` | setup didn't finish — re-run step 3 with `--force` |
| `server did not come up` | `cat ~/.skillhub/server.log` and read the last traceback |
| port already in use | re-run setup with `--port 8788` (also update the MCP registration URL) |
| dashboard is raw JSON / 404 at `/` | web UI not built (pnpm missing) — install pnpm, `cd web && pnpm install && pnpm build`, restart |
| `count: 0` skills | wrong library path — redo step 2, then `setup.sh --force --non-interactive --library …` |
| tiles stay empty after 2 min | run the reporter once by hand and read its output: `python3 reporter/skillhub_report.py --backfill --server http://127.0.0.1:8787` |

## Operate (after install)

You have MCP tools once registered (server name `skillhub`): `overview`,
`search_skills`, `skill_detail`, `health_findings`, `safety_findings`,
`remediation_plan`, `usage_events`. Typical asks and how to serve them:

- *"我有哪些技能 / what do I have?"* → `overview`, then `search_skills`
- *"X 安全吗 / is X safe?"* → `safety_findings` with `skill: X` — findings
  are signals with file:line evidence, not verdicts; show the evidence
- *"哪里坏了 / what's broken?"* → `health_findings`, expand the sections
  with non-zero counts
- *"帮我清理 / clean things up"* → `remediation_plan`. Commands in it are
  pre-quoted; broken-link removals carry a still-dangling-at-execution guard.
  **Restate what you are about to run and get the user's confirmation before
  executing anything from the plan.** Loose-copy replacements can lose local
  edits — never run the commented-out ones without an explicit go-ahead.

Lifecycle: `skillhub` / `skillhub stop` / `skillhub status` /
`skillhub update` (git pull + rebuild web when it changed; then restart).

## Uninstall

```bash
skillhub stop
launchctl unload ~/Library/LaunchAgents/com.skillhub.server.plist 2>/dev/null
rm -f ~/Library/LaunchAgents/com.skillhub.server.plist ~/.local/bin/skillhub
rm -rf ~/.skillhub                # config, logs, pid — the DB if defaulted
claude mcp remove skillhub 2>/dev/null
# then delete the checkout directory; the user's skills library is never touched
```

## Boundaries

- Skillmgmnt is read-only over the user's skills; keep it that way. The one
  hub-side write is the dashboard's own git fast-forward button.
- Don't install system packages, edit shell profiles beyond what setup.sh
  itself does, or bind the server to non-localhost without the user asking.
- The hub has no authentication — if the user wants LAN access
  (`SKILLMGMNT_HOST=0.0.0.0`), say that out loud before enabling it.
