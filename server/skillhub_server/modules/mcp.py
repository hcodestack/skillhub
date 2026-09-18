"""MCP module — the skills a server serves, and who can reach them.

This is the one part of the dashboard that looks outward. Everything else
reads the filesystem; skills served over MCP (SEP-2640) are required to be
cached outside every skill-discovery path, so the filesystem cannot see them
and asking the server is the only way.

The probe is a background job for the same reason the upstream check is: it
makes network calls, which must never sit in a request or the startup path.
"""
import json
import time

from fastapi import APIRouter

from ..core import mcp as probe_client
from ..core.db import get_conn, tx
from ..core.i18n import tr
from ..core.jobs import record
from ..core.quality import est_tokens

router = APIRouter(prefix="/mcp", tags=["mcp"])

STALE_AFTER = 6 * 60 * 60      # re-probe an endpoint at most this often


def _store(row: dict) -> None:
    conn = get_conn()
    now = int(time.time())
    skills = row.get("skills") or []
    chars = sum(len(s["name"]) + len(s["description"]) for s in skills)
    with tx():
        conn.execute(
            "INSERT INTO mcp_endpoints(endpoint,transport,server_name,server_title,"
            "server_version,protocol,skills_ext,directory_read,state,detail,"
            "skills_count,meta_tokens,probed_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) "
            "ON CONFLICT(endpoint) DO UPDATE SET server_name=excluded.server_name, "
            "server_title=excluded.server_title, server_version=excluded.server_version, "
            "protocol=excluded.protocol, skills_ext=excluded.skills_ext, "
            "directory_read=excluded.directory_read, state=excluded.state, "
            "detail=excluded.detail, skills_count=excluded.skills_count, "
            "meta_tokens=excluded.meta_tokens, probed_at=excluded.probed_at",
            (row["endpoint"], row.get("transport", ""), row.get("server_name", ""),
             row.get("server_title", ""), row.get("server_version", ""),
             row.get("protocol", ""), row.get("skills_ext", 0),
             row.get("directory_read", 0), row["state"], row.get("detail", "")[:300],
             len(skills), est_tokens(chars), now))
        for s in skills:
            conn.execute(
                "INSERT INTO mcp_skills(endpoint,uri,name,description,frontmatter,"
                "files,bytes,verifiable,digest,seen_at) VALUES(?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(endpoint,uri) DO UPDATE SET name=excluded.name, "
                "description=excluded.description, frontmatter=excluded.frontmatter, "
                "files=excluded.files, bytes=excluded.bytes, "
                "verifiable=excluded.verifiable, digest=excluded.digest, "
                "seen_at=excluded.seen_at",
                (row["endpoint"], s["uri"], s["name"], s["description"],
                 json.dumps(s["frontmatter"], ensure_ascii=False), s["files"],
                 s["bytes"], s["verifiable"], s["digest"], now))
        # a listing is a complete snapshot for that endpoint
        if skills:
            conn.execute("DELETE FROM mcp_skills WHERE endpoint=? AND seen_at<?",
                         (row["endpoint"], now))
        conn.commit()


def _fail(endpoint: str, err: probe_client.ProbeError) -> None:
    conn = get_conn()
    with tx():
        conn.execute(
            "INSERT INTO mcp_endpoints(endpoint,state,detail,probed_at) VALUES(?,?,?,?) "
            "ON CONFLICT(endpoint) DO UPDATE SET state=excluded.state, "
            "detail=excluded.detail, probed_at=excluded.probed_at",
            (endpoint, err.state, err.detail[:300], int(time.time())))
        conn.commit()


def refresh(force: bool = False) -> dict:
    """Probe every declared endpoint. Recorded, so a silent failure shows."""
    with record("mcp_probe") as run:
        res = _refresh(force)
        run.detail = tr("en", "job.detail.mcp", probed=res["probed"],
                        served=res["served"], skills=res["skills"])
        return res


def _refresh(force: bool = False) -> dict:
    conn = get_conn()
    now = int(time.time())
    rows = conn.execute(
        "SELECT e.endpoint, e.probed_at, e.state, "
        "  (SELECT COUNT(*) FROM mcp_declarations d "
        "   WHERE d.endpoint=e.endpoint AND d.active=1) refs "
        "FROM mcp_endpoints e ORDER BY e.endpoint").fetchall()
    probed = served = skills = skipped = 0
    for r in rows:
        if not r["refs"]:
            continue                                    # nobody points at it any more
        if not force and r["probed_at"] and now - r["probed_at"] < STALE_AFTER:
            skipped += 1
            continue
        try:
            out = probe_client.probe(r["endpoint"])
        except probe_client.ProbeError as e:
            _fail(r["endpoint"], e)
            probed += 1
            continue
        _store(out)
        probed += 1
        if out["state"] == "served":
            served += 1
            skills += len(out["skills"])
    return {"ok": True, "probed": probed, "served": served, "skills": skills,
            "cached": skipped}


def served_skills() -> list[dict]:
    """Every skill currently served, flattened. Used by health and the catalog."""
    conn = get_conn()
    return [dict(r) for r in conn.execute(
        "SELECT s.*, e.server_name, e.state FROM mcp_skills s "
        "JOIN mcp_endpoints e ON e.endpoint=s.endpoint "
        "WHERE e.state IN ('served','empty') ORDER BY s.name").fetchall()]


@router.get("/servers")
def list_servers(lang: str = "en"):
    conn = get_conn()
    out = []
    for e in conn.execute("SELECT * FROM mcp_endpoints ORDER BY endpoint").fetchall():
        decls = [dict(d) for d in conn.execute(
            "SELECT host,agent,scope,project_path,name,has_auth FROM mcp_declarations "
            "WHERE endpoint=? AND active=1 ORDER BY host,agent,name",
            (e["endpoint"],)).fetchall()]
        if not decls:
            continue                                    # retired along with its config
        skills = [dict(s) for s in conn.execute(
            "SELECT uri,name,description,files,bytes,verifiable,digest "
            "FROM mcp_skills WHERE endpoint=? ORDER BY name", (e["endpoint"],)).fetchall()]
        row = {k: e[k] for k in e.keys()}
        row["declarations"] = decls
        row["skills"] = skills
        row["agents"] = sorted({d["agent"] for d in decls})
        row["hosts"] = sorted({d["host"] for d in decls})
        row["has_auth"] = any(d["has_auth"] for d in decls)
        out.append(row)
    totals = {
        "endpoints": len(out),
        "serving": sum(1 for r in out if r["state"] == "served"),
        "skills": sum(r["skills_count"] for r in out),
        "meta_tokens": sum(r["meta_tokens"] for r in out),
        "unprobed": sum(1 for r in out if r["state"] in ("", "declared", "auth")),
    }
    return {"servers": out, "totals": totals}


@router.post("/probe")
def probe_now(force: bool = True):
    return refresh(force=force)
