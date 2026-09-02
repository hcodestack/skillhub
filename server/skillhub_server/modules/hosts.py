"""Hosts module — which machines report in, and what they carry."""
import json
import os
from collections import Counter

from fastapi import APIRouter

from ..core.db import get_conn

router = APIRouter(tags=["hosts"])


@router.get("/hosts")
def list_hosts():
    conn = get_conn()
    hosts = [dict(r) for r in conn.execute("SELECT * FROM hosts ORDER BY id").fetchall()]
    for h in hosts:
        agents = {}
        for r in conn.execute(
                "SELECT agent, COUNT(*) entries, "
                "SUM(CASE WHEN scope='global' THEN 1 ELSE 0 END) global_entries, "
                "SUM(CASE WHEN scope='project' THEN 1 ELSE 0 END) project_entries "
                "FROM installs WHERE host=? AND active=1 GROUP BY agent ORDER BY agent",
                (h["id"],)).fetchall():
            agents[r["agent"]] = {**dict(r), "global_dir": "", "project_dirs": [],
                                  "shared_with": ""}
        # Where each tool reads from: the global entry directory (the one
        # parent that holds its global entries) and the projects it is loaded
        # into. A tool that reads several directories keeps the busiest as its
        # headline path; the rest are visible per skill in the drawer.
        for r in conn.execute(
                "SELECT agent, scope, entry_path, project_path, shared_with "
                "FROM installs WHERE host=? AND active=1", (h["id"],)).fetchall():
            a = agents.get(r["agent"])
            if a is None:
                continue
            if r["scope"] == "global" and r["entry_path"]:
                a.setdefault("_dirs", Counter())[os.path.dirname(r["entry_path"])] += 1
            elif r["scope"] == "project" and r["project_path"]:
                a.setdefault("_projects", set()).add(r["project_path"])
            if r["shared_with"] and not a["shared_with"]:
                a["shared_with"] = r["shared_with"]
        for a in agents.values():
            dirs = a.pop("_dirs", None)
            if dirs:
                a["global_dir"] = dirs.most_common(1)[0][0]
            a["project_dirs"] = sorted(a.pop("_projects", set()))
        h["agents"] = list(agents.values())
        # detected = scanned by the reporter, whether or not anything was found
        try:
            seen = set(json.loads(h.pop("agents_seen") or "[]"))
        except (TypeError, ValueError):
            seen = set()
        h["detected_agents"] = sorted(seen | set(agents))
        row = conn.execute(
            "SELECT COUNT(*) c, MAX(ts) last FROM usage_events WHERE host=?",
            (h["id"],)).fetchone()
        h["events_total"], h["last_event_ts"] = row["c"], row["last"]
    return {"hosts": hosts}
