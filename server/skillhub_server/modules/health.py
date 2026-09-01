"""Health module — governance findings derived from reported state.
Read-only observations; fixing stays with the `skill` CLI per policy."""
from fastapi import APIRouter

import os

from ..core.config import settings
from ..core.quality import (LONG_BODY_LINES, SHORT_DESC_CHARS, body_lines)
from ..core.db import get_conn
from ..core.i18n import tr
from ..core.jobs import last_runs

router = APIRouter(prefix="/health", tags=["health"])

# Sanctioned entries that are legitimately entities in entry dirs — configure
# via SKILLHUB_ENTITY_WHITELIST="agent:entry,agent:entry".
def WHITELIST():
    return settings.entity_whitelist()


@router.get("/findings")
def findings(lang: str = "en"):
    conn = get_conn()
    sections = []

    # First, because everything below it is only as fresh as these three runs.
    # A failed sync or scan used to be visible only in `docker logs`, so the
    # dashboard would keep showing yesterday's numbers with nothing to say so.
    jobs = last_runs(lang)
    bad = [j for j in jobs if j["status"] in ("failed", "stuck")]
    sections.append({
        "key": "background_jobs",
        "severity": "error" if bad else "info",
        "title": tr(lang, "he.jobs.title"),
        "hint": tr(lang, "he.jobs.hint"),
        # count is the item count here as in every other section; whether to
        # worry is what the severity chip says
        "count": len(jobs), "items": jobs,
    })

    rows = [dict(r) for r in conn.execute(
        "SELECT host,agent,scope,project_path,entry_name,entry_path,link_type,vcs "
        "FROM installs WHERE active=1 AND link_type='entity'").fetchall()]
    wl = WHITELIST()
    entity = [r for r in rows if (r["agent"], r["entry_name"]) not in wl]

    # A skill committed inside a cloned repo is not a stray copy — it shipped
    # with that project and is updated by pulling it. Reporting the two together
    # buries the ones that actually need attention.
    loose = [r for r in entity if r["vcs"] != "vendored"]
    vendored = [r for r in entity if r["vcs"] == "vendored"]

    sections.append({
        "key": "loose_entities", "severity": "warn",
        "title": tr(lang, "he.loose.title"),
        "hint": tr(lang, "he.loose.hint"),
        "count": len(loose), "items": loose,
    })
    sections.append({
        "key": "vendored_entities", "severity": "info",
        "title": tr(lang, "he.vendored.title"),
        "hint": tr(lang, "he.vendored.hint"),
        "count": len(vendored), "items": vendored,
    })

    broken = [dict(r) for r in conn.execute(
        "SELECT host,agent,scope,project_path,entry_name,entry_path,target_path "
        "FROM installs WHERE active=1 AND link_type='broken'").fetchall()]
    sections.append({
        "key": "broken_links", "severity": "error",
        "title": tr(lang, "he.broken.title"),
        "hint": tr(lang, "he.broken.hint"),
        "count": len(broken), "items": broken,
    })

    # Separated from the above on purpose: when the NAS is unmounted every
    # symlink into the library fails at once. Counting those as broken would
    # bury the handful that are genuinely stale under a flood, and the fix
    # ("mount the NAS") has nothing to do with the skills.
    unrooted = [dict(r) for r in conn.execute(
        "SELECT host,agent,scope,project_path,entry_name,entry_path,target_path "
        "FROM installs WHERE active=1 AND link_type='unrooted'").fetchall()]
    sections.append({
        "key": "unrooted_links", "severity": "info",
        "title": tr(lang, "he.unrooted.title"),
        "hint": tr(lang, "he.unrooted.hint"),
        "count": len(unrooted), "items": unrooted,
    })

    unresolved = [dict(r) for r in conn.execute(
        "SELECT skill_key, COUNT(*) n, MAX(ts) last, GROUP_CONCAT(DISTINCT agent) agents "
        "FROM usage_events WHERE skill_id IS NULL "
        "GROUP BY skill_key ORDER BY n DESC").fetchall()]
    sections.append({
        "key": "unresolved_usage", "severity": "info",
        "title": tr(lang, "he.unresolved.title"),
        "hint": tr(lang, "he.unresolved.hint"),
        "count": len(unresolved), "items": unresolved,
    })

    # Same skill copied into several tools: fine when identical, a real problem
    # when the copies have drifted apart — nobody knows which one is current.
    dupes = []
    for r in conn.execute(
            "SELECT entry_name, COUNT(*) copies, "
            "COUNT(DISTINCT content_hash) variants, "
            "GROUP_CONCAT(DISTINCT agent) agents "
            "FROM installs WHERE active=1 AND link_type='entity' AND content_hash!='' "
            "AND vcs!='vendored' "
            "GROUP BY entry_name HAVING copies > 1 "
            "ORDER BY variants DESC, copies DESC").fetchall():
        dupes.append({**dict(r), "drifted": r["variants"] > 1})
    drifted = [d for d in dupes if d["drifted"]]
    sections.append({
        "key": "duplicate_copies", "severity": "warn" if drifted else "info",
        "title": tr(lang, "he.dupes.title"),
        "hint": tr(lang, "he.dupes.hint"),
        "count": len(dupes), "items": dupes,
    })

    # Skills on disk that the external index missed (only meaningful when an
    # index file is configured — the built-in scan has no such blind spot).
    if settings.library_index:
        unindexed = []
        known = {r["id"] for r in conn.execute("SELECT id FROM skills").fetchall()}
        for base in settings.library_bases():
            base_name = os.path.basename(base.rstrip(os.sep))
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames
                               if d not in (".git", "node_modules", ".venv")]
                if not any(f.lower() == "skill.md" for f in filenames):
                    continue
                rel = os.path.relpath(dirpath, base)
                if rel == ".":
                    continue
                rid = rel.replace(os.sep, "/")
                if rid not in known and "/".join(rid.split("/")[:2]) not in known:
                    unindexed.append({"path": f"{base_name}/{rel}"})
        sections.append({
            "key": "unindexed_skills", "severity": "warn",
            "title": tr(lang, "he.unindexed.title"),
            "hint": tr(lang, "he.unindexed.hint"),
            "count": len(unindexed), "items": unindexed,
        })

    # Description quality: it is the trigger mechanism and sits in context every
    # turn, so a thin one means the skill silently never fires.
    thin = [dict(r) for r in conn.execute(
        "SELECT id, name, LENGTH(description) chars FROM skills "
        "WHERE in_library=1 AND LENGTH(description) < ? ORDER BY chars",
        (SHORT_DESC_CHARS,)).fetchall()]
    sections.append({
        "key": "thin_descriptions", "severity": "warn",
        "title": tr(lang, "he.thin.title"),
        "hint": tr(lang, "he.thin.hint", n=SHORT_DESC_CHARS),
        "count": len(thin), "items": thin,
    })

    oversized = [{"id": r["id"], "lines": r["body_lines"]} for r in conn.execute(
        "SELECT id, body_lines FROM skills WHERE in_library=1 AND body_lines > ? "
        "ORDER BY body_lines DESC", (LONG_BODY_LINES,)).fetchall()]
    sections.append({
        "key": "oversized_bodies", "severity": "info",
        "title": tr(lang, "he.oversized.title", n=LONG_BODY_LINES),
        "hint": tr(lang, "he.oversized.hint"),
        "count": len(oversized), "items": oversized,
    })

    from .vetting import findings_map
    vets = findings_map(lang)
    risky = []
    for sid, v in vets.items():
        for f in v["findings"]:
            if f["severity"] == "high":
                risky.append({"id": sid, "rule": f["rule"], "category": f["category"],
                              "description": f["description"],
                              "where": f'{f["file"]}:{f["line"]}',
                              "excerpt": f["excerpt"]})
    risky.sort(key=lambda x: x["id"])
    sections.append({
        "key": "safety_high", "severity": "warn",
        "title": tr(lang, "he.safety.title"),
        "hint": tr(lang, "he.safety.hint"),
        "count": len(risky), "items": risky,
    })

    never = [dict(r) for r in conn.execute(
        "SELECT s.id, s.name, s.source, s.category FROM skills s "
        "WHERE s.in_library=1 "
        "AND NOT EXISTS(SELECT 1 FROM usage_events u WHERE u.skill_id=s.id) "
        "AND NOT EXISTS(SELECT 1 FROM installs i WHERE i.skill_id=s.id AND i.active=1) "
        "ORDER BY s.id").fetchall()]
    sections.append({
        "key": "idle_skills", "severity": "info",
        "title": tr(lang, "he.idle.title"),
        "hint": tr(lang, "he.idle.hint"),
        "count": len(never), "items": never,
    })

    return {"sections": sections}
