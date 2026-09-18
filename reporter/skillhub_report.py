#!/usr/bin/env python3
"""Skillhub reporter — scans this machine's agent entry dirs and session logs,
then pushes inventory snapshots + usage events to the hub. Stdlib only, so any
LAN machine can run it with a bare python3.

Usage:
  python3 skillhub_report.py                  # incremental run
  python3 skillhub_report.py --backfill       # ignore cursors, full history
  python3 skillhub_report.py --dry-run        # collect and print counts only

Offline-safe: if the hub is unreachable the payload is spooled locally and
flushed on the next successful run.
"""
import argparse
import fcntl
import json
import os
import platform
import socket
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adapters import claude_code, codex, mcp_config, tools, workbuddy  # noqa: E402

# Usage adapters: parse an agent's own logs into call events. Add one per agent
# that records skill invocations somewhere readable.
USAGE_ADAPTERS = [claude_code, codex, workbuddy]
# Inventory (which skill is loaded where) is collected for ALL installed tools
# by this single scanner — see adapters/tool_table.py.
INVENTORY_SCANNER = tools

STATE_DIR = Path(os.environ.get("SKILLHUB_STATE", str(Path.home() / ".local/state/skillhub")))
STATE_FILE = STATE_DIR / "reporter-state.json"
SPOOL_DIR = STATE_DIR / "spool"
CHUNK = 4000  # max events per POST


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state), encoding="utf-8")
    tmp.replace(STATE_FILE)


def post(server: str, payload: dict) -> bool:
    req = urllib.request.Request(
        f"{server.rstrip('/')}/api/v1/report",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            print(f"[skillhub] posted: {body}")
            return True
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as e:
        print(f"[skillhub] post failed: {e}", file=sys.stderr)
        return False


def spool(payload: dict) -> None:
    SPOOL_DIR.mkdir(parents=True, exist_ok=True)
    # spooled copies must not deactivate rows later: drop snapshot semantics
    # spooled copies must not retire rows later, for MCP declarations either
    payload = {**payload, "snapshot_agents": [], "mcp_servers": []}
    name = SPOOL_DIR / f"{time.strftime('%Y%m%d-%H%M%S')}-{os.getpid()}.json"
    name.write_text(json.dumps(payload), encoding="utf-8")
    print(f"[skillhub] spooled -> {name}", file=sys.stderr)


def flush_spool(server: str) -> None:
    if not SPOOL_DIR.is_dir():
        return
    for f in sorted(SPOOL_DIR.glob("*.json")):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            f.unlink(missing_ok=True)
            continue
        if post(server, payload):
            f.unlink(missing_ok=True)
        else:
            break


def main() -> int:
    ap = argparse.ArgumentParser(description="Skillhub per-machine reporter")
    ap.add_argument("--server", default=os.environ.get("SKILLHUB_SERVER", "http://127.0.0.1:8787"))
    ap.add_argument("--backfill", action="store_true", help="ignore cursors, re-scan full history")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--host-label", default=os.environ.get("SKILLHUB_HOST_LABEL", ""))
    args = ap.parse_args()

    # single-instance lock: hook + launchd may fire concurrently
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    lock = open(STATE_DIR / "reporter.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("[skillhub] another reporter instance is running — skipping")
        return 0

    state = {} if args.backfill else load_state()
    inventory, events, snapshot_agents = [], [], []
    project_roots: list[str] = []
    for ad in USAGE_ADAPTERS:
        try:
            res = ad.collect(state.setdefault(ad.AGENT, {}))
        except Exception as e:  # one broken adapter must not kill the run
            print(f"[skillhub] adapter {ad.AGENT} failed: {e}", file=sys.stderr)
            continue
        events += res.get("events", [])
        project_roots += res.get("project_roots", [])

    try:
        inv = INVENTORY_SCANNER.collect(state.setdefault("tools", {}), project_roots)
        inventory += inv.get("inventory", [])
        if inv.get("snapshot"):
            # a complete scan owns every tool it knows about, so the hub may
            # retire rows for tools whose skills were removed
            snapshot_agents += inv.get("agents", [])
    except Exception as e:
        print(f"[skillhub] inventory scan failed: {e}", file=sys.stderr)

    # which MCP servers this machine's tools point at. Skills served over MCP
    # never land in a skills directory, so the scan above cannot see them; this
    # is the client-side half of making them visible. Credentials are never read.
    mcp_servers = []
    try:
        mcp_servers = mcp_config.collect(project_roots)
    except Exception as e:
        print(f"[skillhub] mcp config scan failed: {e}", file=sys.stderr)

    host = args.host_label or socket.gethostname().removesuffix(".local")
    base = {"host": host, "os": f"{platform.system()} {platform.release()}",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
    print(f"[skillhub] host={host} inventory={len(inventory)} events={len(events)} "
          f"mcp={len(mcp_servers)} snapshot={snapshot_agents}")
    if args.dry_run:
        by_agent: dict[str, int] = {}
        for e in events:
            by_agent[e["agent"]] = by_agent.get(e["agent"], 0) + 1
        print(json.dumps({"events_by_agent": by_agent}, ensure_ascii=False))
        return 0

    payloads = []
    first = {**base, "inventory": inventory, "events": events[:CHUNK],
             "snapshot_agents": snapshot_agents, "mcp_servers": mcp_servers}
    payloads.append(first)
    for i in range(CHUNK, len(events), CHUNK):
        payloads.append({**base, "inventory": [], "events": events[i:i + CHUNK],
                         "snapshot_agents": []})

    ok = True
    for p in payloads:
        if not post(args.server, p):
            ok = False
            spool(p)
    save_state(state)  # events are either delivered or spooled; cursors advance
    if ok:
        flush_spool(args.server)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
