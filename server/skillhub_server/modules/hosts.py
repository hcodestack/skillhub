"""Hosts module — which machines report in, and what they carry."""
from fastapi import APIRouter

from ..core.db import get_conn

router = APIRouter(tags=["hosts"])


@router.get("/hosts")
def list_hosts():
    conn = get_conn()
    hosts = [dict(r) for r in conn.execute("SELECT * FROM hosts ORDER BY id").fetchall()]
    for h in hosts:
        h["agents"] = [dict(r) for r in conn.execute(
            "SELECT agent, COUNT(*) entries, "
            "SUM(CASE WHEN scope='global' THEN 1 ELSE 0 END) global_entries, "
            "SUM(CASE WHEN scope='project' THEN 1 ELSE 0 END) project_entries "
            "FROM installs WHERE host=? AND active=1 GROUP BY agent ORDER BY agent",
            (h["id"],)).fetchall()]
        row = conn.execute(
            "SELECT COUNT(*) c, MAX(ts) last FROM usage_events WHERE host=?",
            (h["id"],)).fetchone()
        h["events_total"], h["last_event_ts"] = row["c"], row["last"]
    return {"hosts": hosts}
