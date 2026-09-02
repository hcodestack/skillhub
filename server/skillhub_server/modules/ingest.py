"""Ingest module — receives inventory snapshots and usage events pushed by
per-machine reporters. Idempotent: events carry a content hash; inventory is a
full per-agent snapshot that upserts and deactivates missing rows."""
import hashlib
import json
import time

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..core import resolve as R
from ..core.config import settings
from ..core.db import get_conn, tx
from .library import sync_if_changed

router = APIRouter(tags=["ingest"])


class InvItem(BaseModel):
    agent: str
    scope: str = "global"          # global | project
    project_path: str = ""
    entry_name: str
    entry_path: str = ""
    link_type: str = "symlink"     # symlink | entity | broken | unrooted
    target_path: str = ""
    shared_with: str = ""          # display names of tools sharing this dir
    content_hash: str = ""         # entity dirs only
    vcs: str = ""                  # entity only: vendored | untracked | loose
    skill_name: str = ""           # SKILL.md frontmatter
    skill_desc: str = ""


class UsageItem(BaseModel):
    agent: str
    skill_key: str
    ts: str
    project: str = ""
    session_id: str = ""
    source: str = ""
    hash: str = ""
    extra: str = ""


class Report(BaseModel):
    host: str
    os: str = ""
    ts: str = ""
    inventory: list[InvItem] = Field(default_factory=list)
    events: list[UsageItem] = Field(default_factory=list)
    # agents whose inventory in this payload is a COMPLETE snapshot for the host
    snapshot_agents: list[str] = Field(default_factory=list)


@router.post("/report")
def report(r: Report):
    conn = get_conn()
    sync_if_changed()  # pick up skills added to the library since the last report
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    exact, by_base, source_of = R.build_key_maps(conn)
    lib_root = settings.library_root_path
    ins = upd = ev = 0
    with tx():
        # snapshot_agents is the reporter's list of tools it actually scanned —
        # i.e. whose home directory exists — including ones holding no skill.
        # That is the "detected" set the hosts page shows; without it a tool
        # with zero entries is indistinguishable from one not installed.
        conn.execute(
            "INSERT INTO hosts(id,os,last_report_at,agents_seen) VALUES(?,?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET os=excluded.os, "
            "last_report_at=excluded.last_report_at, "
            "agents_seen=CASE WHEN excluded.agents_seen='[]' THEN hosts.agents_seen "
            "ELSE excluded.agents_seen END",
            (r.host, r.os, now, json.dumps(sorted(r.snapshot_agents))))

        for it in r.inventory:
            sid = R.target_to_id(it.target_path, lib_root, exact)
            if not sid:
                sid, _ = R.resolve_key(it.entry_name, exact, by_base, source_of, conn)
            cur = conn.execute(
                "SELECT id FROM installs WHERE host=? AND agent=? AND scope=? "
                "AND project_path=? AND entry_name=?",
                (r.host, it.agent, it.scope, it.project_path, it.entry_name)).fetchone()
            if cur:
                conn.execute(
                    "UPDATE installs SET entry_path=?, link_type=?, target_path=?, "
                    "skill_id=?, shared_with=?, content_hash=?, skill_name=?, "
                    "skill_desc=?, vcs=?, last_seen=?, active=1 WHERE id=?",
                    (it.entry_path, it.link_type, it.target_path, sid, it.shared_with,
                     it.content_hash, it.skill_name, it.skill_desc, it.vcs, now,
                     cur["id"]))
                upd += 1
            else:
                conn.execute(
                    "INSERT INTO installs(host,agent,scope,project_path,entry_name,entry_path,"
                    "link_type,target_path,skill_id,shared_with,content_hash,skill_name,"
                    "skill_desc,vcs,first_seen,last_seen,active) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,1)",
                    (r.host, it.agent, it.scope, it.project_path, it.entry_name,
                     it.entry_path, it.link_type, it.target_path, sid, it.shared_with,
                     it.content_hash, it.skill_name, it.skill_desc, it.vcs, now, now))
                ins += 1

        for agent in r.snapshot_agents:
            seen = {(it.scope, it.project_path, it.entry_name)
                    for it in r.inventory if it.agent == agent}
            for row in conn.execute(
                    "SELECT id,scope,project_path,entry_name FROM installs "
                    "WHERE host=? AND agent=? AND active=1", (r.host, agent)).fetchall():
                if (row["scope"], row["project_path"], row["entry_name"]) not in seen:
                    conn.execute("UPDATE installs SET active=0, last_seen=? WHERE id=?",
                                 (now, row["id"]))

        for e in r.events:
            h = e.hash or hashlib.sha1(
                f"{r.host}|{e.agent}|{e.source}|{e.skill_key}|{e.session_id}|{e.ts}"
                .encode()).hexdigest()
            sid, note = R.resolve_key(e.skill_key, exact, by_base, source_of, conn)
            res = conn.execute(
                "INSERT OR IGNORE INTO usage_events"
                "(hash,host,agent,skill_key,skill_id,project,session_id,ts,source,extra) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (h, r.host, e.agent, e.skill_key, sid, e.project, e.session_id,
                 e.ts, e.source, e.extra or note))
            ev += res.rowcount
        conn.commit()
    return {"ok": True, "installs_new": ins, "installs_updated": upd, "events_new": ev}


def reresolve_all(conn) -> None:
    """After a library sync, retry resolution of previously-unresolved rows."""
    exact, by_base, source_of = R.build_key_maps(conn)
    lib_root = settings.library_root_path
    with tx():
        for row in conn.execute(
                "SELECT hash, skill_key FROM usage_events WHERE skill_id IS NULL").fetchall():
            sid, _ = R.resolve_key(row["skill_key"], exact, by_base, source_of, conn)
            if sid:
                conn.execute("UPDATE usage_events SET skill_id=? WHERE hash=?",
                             (sid, row["hash"]))
        for row in conn.execute(
                "SELECT id, entry_name, target_path FROM installs WHERE skill_id IS NULL").fetchall():
            sid = R.target_to_id(row["target_path"] or "", lib_root, exact)
            if not sid:
                sid, _ = R.resolve_key(row["entry_name"], exact, by_base, source_of, conn)
            if sid:
                conn.execute("UPDATE installs SET skill_id=? WHERE id=?", (sid, row["id"]))
        conn.commit()
