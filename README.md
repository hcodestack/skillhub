<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/hero-topology-dark.png">
  <img src="docs/assets/hero-topology-light.png" alt="Skillhub topology — every skill, every tool it is loaded into, colored by link health" width="920">
</picture>

# Skillhub

**The read-only observability dashboard for your AI-agent skills.**
See every skill you own, every tool that loads it, what actually gets used — and what's silently broken.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776ab.svg)](https://www.python.org)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](web/)
[![Agent-installable](https://img.shields.io/badge/install-by%20your%20agent-8a2be2.svg)](AGENTS.md)

**English** · [简体中文](README.zh-CN.md)

</div>

---

Skills (`SKILL.md` folders) are how AI coding tools learn your workflows — and
they multiply fast: one library, a dozen tools, symlinks here, copies there,
leftovers everywhere. Skillhub answers the four questions nobody can answer by
hand anymore:

1. **What do I have?** — a searchable catalog of your whole skills library
2. **Where is it loaded?** — which of **47+ AI tools** (Claude Code, Codex,
   Cursor, Gemini CLI, Copilot, Cline, …) load each skill, globally or
   per-project, as a symlink or a copy
3. **Is it used?** — invocation events parsed from the tools' own session logs
4. **What's broken?** — broken symlinks, stray copies, drifted duplicates,
   oversized bodies, descriptions too thin to ever trigger, and a
   deterministic **safety review** of what each skill's code actually does

## ✨ Features

| | |
|---|---|
| 🗺 **Load topology** | A three-level Sankey — domain → skill → every load site — colored by link health (symlink / repo-vendored / stray copy / broken), with drill-down and a table view |
| 🔍 **47+ tool coverage** | One scanner knows the entry directories of 47+ AI coding tools; shared directories are attributed honestly (`shared:<dir>`), never to one arbitrary tool |
| 📈 **Real usage, not vibes** | Skill invocations parsed incrementally from session logs, per tool and per skill — sortable, filterable, time-lined |
| 🩺 **Governance findings** | Broken links (with an unmounted-volume guard so one offline disk doesn't flood the page red), stray copies, content-drifted duplicates, thin descriptions, oversized bodies — each explained in place: what it is, how it happens, what to do |
| 🛡 **Deterministic safety review** | 12 regex rules with a cross-line window scan every skill's files for credential access, outbound POSTs, `curl \| sh`, eval/exec, sudo and more — no model, no API key, no network. Findings are signals with file:line evidence, not verdicts |
| 🔄 **Upstream updates** | git-backed skills that fell behind get a one-click `git pull --ff-only` (refuses dirty trees); catalog-copied skills report upstream movement |
| 📋 **Findings → action** | Export a governance report (paste it to your agent as a work order) or a reviewable remediation script whose *uncommented* commands are provably safe |
| 🤖 **MCP native** | Seven read-only tools let Claude Code / Codex query the hub directly: *"which skills does nobody use?" "is X safe?" "fetch the remediation plan"* — your agent executes, with your confirmation, on the machine where the files are |
| 🖥 **Runs anywhere** | One machine (built-in self-reporter, zero cron), Docker, or a LAN hub on a home server/NAS aggregating every machine you work on |
| 🔒 **Read-only by design** | Skillhub observes; your existing workflow keeps managing. It can never fight your tooling or move your files |

<div align="center">
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/overview-dark.png">
  <img src="docs/assets/overview-light.png" alt="Skillhub overview — stat tiles and the full skill catalog" width="920">
</picture>
<br><sub>The overview: problem tiles deep-link straight into their findings.</sub>
</div>

## 🚀 Quick start

| You have… | Mode | Setup |
|---|---|---|
| one machine | **A · Local** | the wizard below — no cron, no Docker |
| one machine + Docker | **B · Docker** | container + a tiny host-side reporter |
| several machines / NAS | **C · LAN hub** | server on the always-on box, reporters everywhere |

### Mode A — local (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/hcodestack/skillhub/main/install.sh | bash
```

or, from a clone:

```bash
git clone https://github.com/hcodestack/skillhub.git ~/skillhub
cd ~/skillhub && ./setup.sh
```

The wizard shows which AI tools it detected on your machine, asks where your
skills library is (any folder tree containing `SKILL.md` directories — no
manifest, no naming convention), builds the UI once, installs the `skillhub`
command, and offers start-at-login plus one-keystroke MCP registration with
Claude Code. Bilingual, five steps, no questions it can answer itself.

Day-to-day:

```bash
skillhub          # start (if needed) and open the dashboard
skillhub status   # running? watching which library?
skillhub update   # pull the latest, rebuild if needed
skillhub stop
```

A built-in self-reporter scans this machine's AI tools every 15 minutes
(first run backfills usage history) — nothing else to schedule. Its runs
appear on the health page like any background job, so failures are loud.

*Prerequisites: Python 3.11+ with [uv](https://docs.astral.sh/uv); Node with
pnpm only for the one-time UI build. No skills library yet? `./quickstart.sh`
boots against the bundled demo library.*

### 🤖 Don't like terminals? Let your agent install it

Skillhub ships an **agent runbook** ([AGENTS.md](AGENTS.md)) that Claude
Code, Codex and similar tools follow: what to check, what to ask you (in your
language), how to find your skills library, the exact non-interactive install,
and how to *prove* the result before reporting back. Paste this into your
agent:

> Install Skillhub on this machine: clone
> `https://github.com/hcodestack/skillhub` to `~/skillhub`, then read
> `AGENTS.md` in the checkout and follow its Install runbook. Ask me only
> what it tells you to ask. When you're done, show me what my dashboard says.

Because setup registers the hub as an MCP tool, the same agent can answer
*"which skills does nobody use?"* or *"clean up my broken links"* the moment
the install finishes.

### Mode B — Docker on one machine

```bash
cd web && pnpm build
docker build -f deploy/Dockerfile.release -t skillhub:latest .
# edit deploy/docker-compose.yml: mount your library at /library
docker compose -f deploy/docker-compose.yml up -d

# a container can't scan your host $HOME — run the reporter on the host:
reporter/install-launchd.sh http://127.0.0.1:8787     # macOS, every 15 min
reporter/install-cron.sh    http://127.0.0.1:8787     # Linux, every 15 min
```

### Mode C — LAN hub (home server / NAS)

Run Mode B on the always-on box, then on **each** machine you work on:

```bash
reporter/install-launchd.sh http://<hub-host>:8787    # or install-cron.sh
```

Every machine appears on the **Hosts** tab; findings aggregate across all of
them. Add `:ro` to the library mount unless you want one-click git updates.

## 🧭 How it works

```
Any host (laptop, home server, NAS)            each machine you work on
┌──────────────────────────────┐  HTTP POST   ┌──────────────────────────────┐
│ server/  FastAPI + SQLite    │ ◄─────────── │ reporter/skillhub_report.py  │
│  · scans your skills library │  /api/v1/    │  · scans 47+ tool entry dirs │
│  · background: upstream      │   report     │  · parses session logs       │
│    checks, safety review     │              │    incrementally (cursors)   │
│  · web/ SPA (React 19)       │              │  · offline spool + catch-up  │
└──────────────────────────────┘              │  pure stdlib, zero deps      │
        ▲                                     └──────────────────────────────┘
        └──────────────────────────────────── ┌──────────────────────────────┐
              HTTP GET  /api/v1/*             │ mcp/skillhub_mcp.py          │
                                              │ read-only, stdio ↔ your agent│
                                              └──────────────────────────────┘
```

The server is the only required part. Skill ids are simply paths relative to
your library root — the hub scans for `SKILL.md` folders itself; an external
index file is optional for setups that already maintain a catalog.

## ⚙️ Configuration

Everything is environment variables; only the first is required.

| Variable | Meaning |
|---|---|
| `SKILLHUB_LIBRARY_ROOT` | your skills library directory (scanned recursively for `SKILL.md`) |
| `SKILLHUB_LIBRARY_INDEX` | *optional*: pre-built JSON catalog used instead of scanning; re-synced on mtime change |
| `SKILLHUB_LIBRARY_SUBDIRS` | *optional*, comma-separated: restrict lookup to these first-level subdirs |
| `SKILLHUB_INSTALLER_SUBDIR` | *optional*: one subdir owned by an installer CLI (hub labels, never updates) |
| `SKILLHUB_ENTITY_WHITELIST` | *optional*: `agent:entry,…` pairs that are legitimately real dirs in tool entry dirs |
| `SKILLHUB_PROVENANCE_FILE` | *optional*: JSON mapping skill families to upstream repos (schema in `core/provenance.py`) |
| `SKILLHUB_LIBRARY_DISPLAY_ROOT` | library path as *users* see it, for copy-pasteable commands when the hub runs in Docker |
| `SKILLHUB_SELF_REPORT` | `auto` (default) / `1` / `0` — the built-in self-reporter; auto = on for source checkouts outside containers |
| `SKILLHUB_DB` / `SKILLHUB_HOST` / `SKILLHUB_PORT` / `SKILLHUB_STATIC` | storage & serving knobs |

> **Note** · The dashboard has no authentication — it binds to `127.0.0.1` by
> default. Set `SKILLHUB_HOST=0.0.0.0` only on a network you trust.
> The dashboard UI is currently Chinese-first; i18n contributions are welcome.

## 🛡 Why the safety review exists

Every skill is code someone else wrote that your agent runs **with your
permissions**. On every sync, Skillhub runs a deterministic red-flag review
over every file a skill ships: reading agent memory/credential files, browser
session access, raw-IP endpoints, `curl | sh`, eval/exec on external input,
sudo, out-of-tree writes, outbound POSTs, unpinned installs,
base64-decode-then-run. Findings carry file, line, excerpt and rationale —
signals for a human (or your agent) to judge, never silent verdicts.

## 🧱 Deliberate non-features

- **No built-in model evaluation** — skill quality grading belongs to tools
  purpose-built for it; the hub generates a ready-to-paste evaluation prompt
  instead of embedding an LLM client (no keys, no bills)
- **No usage trend charts** until the data earns them — with sparse logs a
  trend line is theater; the sortable table tells the truth
- **No chat memory** — transcripts already live where your tools keep them
- **No write operations on your skills** — the one hub-side write is the
  optional git fast-forward button, and the MCP surface is read-only

## 📄 License

[MIT](LICENSE) © 2026 [hcodestack](https://github.com/hcodestack)
