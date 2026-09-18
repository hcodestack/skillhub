"""Skills query module — the aggregated list that powers the dashboard, the
per-skill event timeline, and the stat tiles."""
import datetime as dt
import json

from fastapi import APIRouter

from ..core.config import settings
from ..core.db import get_conn
from ..core.i18n import tr
from ..core.quality import est_tokens
from .library import classify
from .sources import status_map
from .vetting import findings_map

router = APIRouter(tags=["skills"])


def _days_ago(n: int) -> str:
    return (dt.date.today() - dt.timedelta(days=n)).isoformat()


def _item_key(skill_id: str | None, skill_key: str) -> str:
    return skill_id if skill_id else f"?key:{skill_key}"


@router.get("/skills")
def list_skills(lang: str = "en"):
    conn = get_conn()
    items: dict[str, dict] = {}

    for s in conn.execute("SELECT * FROM skills WHERE in_library=1").fetchall():
        items[s["id"]] = {
            "key": s["id"], "id": s["id"], "name": s["name"] or s["id"],
            "description": s["description"], "source": s["source"],
            "category": s["category"], "tags": json.loads(s["tags"] or "[]"),
            "in_library": True, "agents": [], "installs": [],
            "body_lines": s["body_lines"], "desc_chars": len(s["description"] or ""),
            "usage": {"total": 0, "d7": 0, "d30": 0, "last": None},
            "agent_usage": {},
        }

    for r in conn.execute("SELECT * FROM installs WHERE active=1").fetchall():
        # unmanaged copies of one skill land in many tools; group them by entry
        # name so seven copies read as one skill in seven places, not seven rows
        key = r["skill_id"] or f"?entry:{r['entry_name']}"
        it = items.get(key)
        if it is None:
            # unmanaged skills were never classified — the library sync only sees
            # what is in the catalog — so derive their tags from the SKILL.md
            # frontmatter the reporter captured, same rules as library skills
            nm = r["skill_name"] or r["entry_name"]
            _, utags = classify(r["entry_name"], nm, r["skill_desc"] or "")
            it = items[key] = {
                "key": key, "id": None,
                "name": nm,
                "description": (r["skill_desc"]
                                or tr(lang, "skill.unmanagedDesc")),
                "source": "unmanaged", "category": "unmanaged", "tags": utags,
                "in_library": False, "agents": [], "installs": [],
                "usage": {"total": 0, "d7": 0, "d30": 0, "last": None},
                "agent_usage": {},
            }
        elif not it["in_library"] and r["skill_desc"] and not it.get("_desc_set"):
            it["description"] = r["skill_desc"]
            it["name"] = r["skill_name"] or it["name"]
            if not it["tags"]:
                _, it["tags"] = classify(r["entry_name"], it["name"], r["skill_desc"])
            it["_desc_set"] = True
        it["installs"].append({
            "host": r["host"], "agent": r["agent"], "scope": r["scope"],
            "project_path": r["project_path"], "entry_name": r["entry_name"],
            "entry_path": r["entry_path"], "link_type": r["link_type"],
            "target_path": r["target_path"], "last_seen": r["last_seen"],
            "shared_with": r["shared_with"], "content_hash": r["content_hash"],
            "vcs": r["vcs"],
        })
        if r["agent"] not in it["agents"]:
            it["agents"].append(r["agent"])

    d7, d30 = _days_ago(7), _days_ago(30)
    for r in conn.execute(
            "SELECT skill_id, skill_key, agent, COUNT(*) n, MAX(ts) last, "
            "SUM(CASE WHEN ts>=? THEN 1 ELSE 0 END) d7, "
            "SUM(CASE WHEN ts>=? THEN 1 ELSE 0 END) d30 "
            "FROM usage_events GROUP BY COALESCE(skill_id, '?key:'||skill_key), agent",
            (d7, d30)).fetchall():
        key = _item_key(r["skill_id"], r["skill_key"])
        if key.startswith("?key:"):
            alt = f"?entry:{r['skill_key']}"   # merge with the unmanaged entry
            if alt in items:
                key = alt
        it = items.get(key)
        if it is None:
            it = items[key] = {
                "key": key, "id": None, "name": r["skill_key"],
                "description": tr(lang, "skill.unresolvedDesc"),
                "source": "unresolved", "category": "external", "tags": [],
                "in_library": False, "agents": [], "installs": [],
                "usage": {"total": 0, "d7": 0, "d30": 0, "last": None},
                "agent_usage": {},
            }
        u = it["usage"]
        u["total"] += r["n"]
        u["d7"] += r["d7"] or 0
        u["d30"] += r["d30"] or 0
        u["last"] = max(u["last"] or "", r["last"] or "") or None
        it["agent_usage"][r["agent"]] = it["agent_usage"].get(r["agent"], 0) + r["n"]
        if r["agent"] not in it["agents"]:
            it["agents"].append(r["agent"])

    srcs = status_map()
    vets = findings_map(lang)
    disp = settings.library_display_path
    for k, it in items.items():
        it["update"] = srcs.get(k)   # None = origin unknown, cannot be checked
        it["vetting"] = vets.get(k)  # None = clean or not yet scanned
        # path as the user sees it, so the UI can build a runnable command
        # Resolve through the configured bases rather than assuming a folder
        # name, then rewrite to the path the user's own machine sees, so the
        # copy button and the evaluation prompt produce something runnable.
        it["library_path"] = ""
        if it["in_library"]:
            d = settings.skill_dir(it["id"])
            root = settings.library_root_path
            if d and disp and root and d.startswith(root):
                it["library_path"] = disp + d[len(root):]
            elif d:
                it["library_path"] = d

    ordered = sorted(items.values(),
                     key=lambda x: (-x["usage"]["total"], x["name"].lower()))
    return {"items": ordered, "generated_at": dt.datetime.now().isoformat(timespec="seconds")}


@router.get("/skills/events")
def skill_events(k: str, limit: int = 100, offset: int = 0):
    """Timeline for one dashboard item; `k` is the item key
    (library id, or '?key:<raw>' for unresolved usage)."""
    conn = get_conn()
    if k.startswith("?key:"):
        where, arg = "skill_id IS NULL AND skill_key=?", k[5:]
    elif k.startswith("?entry:"):
        where, arg = "skill_id IS NULL AND skill_key=?", k[7:]
    else:
        where, arg = "skill_id=?", k
    rows = conn.execute(
        f"SELECT host,agent,skill_key,project,session_id,ts,source FROM usage_events "
        f"WHERE {where} ORDER BY ts DESC LIMIT ? OFFSET ?",
        (arg, limit, offset)).fetchall()
    total = conn.execute(
        f"SELECT COUNT(*) c FROM usage_events WHERE {where}", (arg,)).fetchone()["c"]
    return {"total": total, "events": [dict(r) for r in rows]}


@router.get("/stats/tiles")
def tiles():
    conn = get_conn()
    q = lambda sql, *a: conn.execute(sql, a).fetchone()["c"]  # noqa: E731
    d7 = _days_ago(7)
    return {
        "library_total": q("SELECT COUNT(*) c FROM skills WHERE in_library=1"),
        "loaded_skills": q("SELECT COUNT(DISTINCT COALESCE(skill_id, agent||':'||entry_name)) c "
                           "FROM installs WHERE active=1"),
        "events_total": q("SELECT COUNT(*) c FROM usage_events"),
        "events_d7": q("SELECT COUNT(*) c FROM usage_events WHERE ts>=?", d7),
        # only loose copies are a governance problem; a repo-tracked skill came
        # with someone's project and is updated by pulling it
        "loose_entries": q("SELECT COUNT(*) c FROM installs WHERE active=1 "
                           "AND link_type='entity' AND vcs!='vendored'"),
        "vendored_entries": q("SELECT COUNT(*) c FROM installs WHERE active=1 "
                              "AND link_type='entity' AND vcs='vendored'"),
        "broken_links": q("SELECT COUNT(*) c FROM installs WHERE active=1 "
                          "AND link_type='broken'"),
        "tools": q("SELECT COUNT(DISTINCT agent) c FROM installs WHERE active=1"),
        "hosts": q("SELECT COUNT(*) c FROM hosts"),
        # name+description of every loaded skill sits in context on every turn
        "library_root": settings.library_display_path,
        "metadata_tokens": est_tokens(conn.execute(
            "SELECT COALESCE(SUM(LENGTH(s.name) + LENGTH(s.description)), 0) c "
            "FROM skills s WHERE s.in_library=1 AND EXISTS("
            "  SELECT 1 FROM installs i WHERE i.skill_id = s.id AND i.active=1)"
        ).fetchone()["c"]),
    }
