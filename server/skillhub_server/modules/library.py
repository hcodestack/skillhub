"""Library module — sync the skill catalog.

Two sources, in order of preference:
  1. SKILLHUB_LIBRARY_INDEX, if set and readable — a pre-built JSON catalog
     maintained by an external tool; the hub re-syncs when its mtime changes.
  2. Otherwise the hub scans SKILLHUB_LIBRARY_ROOT itself: every directory
     holding a SKILL.md becomes a skill, its id the path relative to the
     library root. No layout convention, no extra tooling required.
"""
import json
import os
import re
import time

from fastapi import APIRouter

from ..core.config import settings
from ..core.db import get_conn, tx
from ..core.i18n import tr
from ..core.jobs import record
from ..core.quality import BLOCK_SCALAR_ARTIFACTS, body_lines, read_description

router = APIRouter(prefix="/library", tags=["library"])

# Domain tagging rules: (tag key, keyword regex on id+name+description).
#
# The tag is a stable key, not display text — it is stored in the DB and the
# browser renders it in the reader's language (web/src/lib/i18n.tsx, `cat.*`).
# The patterns stay bilingual: they match what skills actually say about
# themselves, and plenty of them say it in Chinese.
DOMAIN_RULES = [
    # Order matters: the first match becomes the primary tag, so a specific
    # domain must be tested before a broader one. Tokens are kept narrow —
    # a generic word like "render" once put "render Mermaid diagrams" under
    # video, which is how a tag stops meaning anything.
    ("meta", r"skill[- ]creator|skill.library|skill.hub|"
             r"skill building|skill\.md|创建技能|技能库|技能编写"),
    ("office", r"\blark\b|飞书|feishu|\bemail\b|gmail|notion|airtable|calendar|"
               r"邮件|日历|审批|考勤"),
    ("audio", r"\btts\b|text[- ]to[- ]speech|speech[- ]to[- ]text|voice|"
              r"audio|sound effect|\bmusic\b|语音|配音|音频|音效|音乐"),
    ("video", r"\bvideo\b|animation|anime\.?js|remotion|\bgsap\b|"
              r"motion|keyframe|视频|动画|动效|关键帧|短剧|分镜"),
    ("3d", r"\brig\b|rigging|character|avatar|\b3d\b|three\.?js|webgl|shader|blender|骨骼|角色|绑定"),
    ("image", r"\bimage\b|illustration|poster|cover|\bsvg\b|figure|comfyui|图像|图片|封面|插画|海报"),
    ("design", r"design system|\bui\b|\bux\b|figma|tailwind|界面设计|视觉规范|设计系统"),
    ("docs", r"docx|xlsx|pptx|\bpdf\b|word document|excel|powerpoint|spreadsheet|"
             r"文档|表格|幻灯片|演示文稿"),
    ("cn-social", r"小红书|xiaohongshu|抖音|douyin|微信|wechat|公众号|gzh|bilibili|b站|"
                  r"快手|kuaishou|微博|weibo|视频号"),
    ("seo", r"\bseo\b|marketing|growth|copywriting|advertis|营销|投放|获客|文案"),
    ("writing", r"writer|writing|humanizer|\barticle\b|blog post|写作|润色|改写"),
    ("web", r"web[- ]?access|browser|scrape|crawl|search the web|tavily|firecrawl|"
            r"联网|抓取|爬虫"),
    ("data", r"\bsql\b|analytics|dashboard|chart|data analysis|visuali[sz]ation|"
             r"数据分析|报表|统计"),
    ("dev", r"cloudflare|workers|wrangler|deploy|\bsdk\b|\bcli\b|\bapi\b|devops|"
            r"turnstile|durable object|部署|运维"),
]

# a skill id with no vendor prefix belongs to no family; "standalone" is a key
# the UI translates, like the domain tags above
STANDALONE = "standalone"


def classify(sid: str, name: str, desc: str) -> tuple[str, list[str]]:
    vendor = sid.split("/")[0] if "/" in sid else STANDALONE
    text = f"{sid} {name} {desc}".lower()
    tags = [tag for tag, pat in DOMAIN_RULES if re.search(pat, text)][:3]
    return vendor, tags


def _index_mtime() -> float:
    if not settings.library_index:
        return 0.0
    try:
        return os.path.getmtime(settings.library_index)
    except OSError:
        return 0.0


SCAN_SKIP = {".git", "node_modules", ".venv", "venv", "__pycache__",
             "dist", "build", "site-packages"}
SCAN_DEPTH = 4          # library-root levels a SKILL.md may sit below


def _scan_library() -> list[dict]:
    """Index rows discovered from disk: any directory with a SKILL.md.

    A skill that nests other skills is cut at the outer boundary — once a
    directory is identified as a skill its subtree is not descended, matching
    how agent tools treat skill directories."""
    from ..core.quality import read_description  # local import: avoids a cycle
    rows: list[dict] = []
    for base in settings.library_bases():
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames
                           if d not in SCAN_SKIP and not d.startswith(".")]
            rel = os.path.relpath(dirpath, base)
            depth = 0 if rel == "." else rel.count(os.sep) + 1
            if depth > SCAN_DEPTH:
                dirnames[:] = []
                continue
            if any(f.lower() == "skill.md" for f in filenames) and rel != ".":
                sid = rel.replace(os.sep, "/")
                rows.append({
                    "id": sid,
                    "name": sid.split("/")[-1],
                    "description": read_description(settings.library_root_path, sid),
                    "source": "library",
                })
                dirnames[:] = []
    return rows


def sync_if_changed() -> None:
    """Re-sync when the index file changed on disk. Without this, a skill added
    to the library lingers as 'unmanaged' until the hub restarts.

    Only applies in index-file mode: in self-scan mode there is no cheap
    change signal, so the scan runs at startup and on POST /library/sync."""
    mtime = _index_mtime()
    if not mtime:
        return
    row = get_conn().execute(
        "SELECT v FROM meta WHERE k='library_index_mtime'").fetchone()
    if row and row["v"] == repr(mtime):
        return
    sync_library()


def sync_library() -> dict:
    """Wrapper so the run is recorded. An unreadable index is returned as
    {"ok": False} rather than raised, so the failure is marked explicitly —
    this is the one that fires when the library is not mounted, and it is
    exactly when the dashboard would otherwise go quietly stale."""
    with record("library_sync") as run:
        res = _sync_library()
        if res.get("ok"):
            run.detail = tr("en", "job.detail.synced", n=res["count"])
        else:
            run.ok = False
            run.detail = res.get("error", "")
        return res


def _sync_library() -> dict:
    conn = get_conn()
    # read the mtime before the file, so a write racing this sync is caught next time
    mtime = _index_mtime()
    if settings.library_index:
        try:
            with open(settings.library_index, encoding="utf-8") as f:
                data = json.load(f)
        except OSError as e:
            return {"ok": False, "error": f"index not readable (volume unmounted?): {e}"}
    elif settings.library_root_path:
        data = _scan_library()
    else:
        return {"ok": False,
                "error": "no library configured — set SKILLHUB_LIBRARY_ROOT"}
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    ids: set[str] = set()
    with tx():
        for row in data:
            sid = (row.get("id") or "").strip()
            if not sid:
                continue
            ids.add(sid)
            desc = (row.get("description") or "").strip()
            if desc in BLOCK_SCALAR_ARTIFACTS:
                desc = read_description(settings.library_root_path, sid) or desc
            vendor, tags = classify(sid, row.get("name", ""), desc)
            conn.execute(
                """INSERT INTO skills(id,name,description,source,category,tags,in_library,first_seen,last_seen)
                   VALUES(?,?,?,?,?,?,1,?,?)
                   ON CONFLICT(id) DO UPDATE SET
                     name=excluded.name, description=excluded.description,
                     source=excluded.source, category=excluded.category,
                     tags=excluded.tags, in_library=1, last_seen=excluded.last_seen""",
                (sid, row.get("name", ""), desc,
                 row.get("source", ""), vendor,
                 json.dumps(tags, ensure_ascii=False), now, now))
        # SKILL.md length is read here, not per request: it means one NAS read
        # per skill on sync instead of 241 on every dashboard load
        for sid in ids:
            conn.execute("UPDATE skills SET body_lines=? WHERE id=?",
                         (body_lines(settings.library_root_path, sid), sid))
        if ids:
            ph = ",".join("?" * len(ids))
            conn.execute(f"UPDATE skills SET in_library=0 WHERE id NOT IN ({ph})", tuple(ids))
        conn.execute(
            "INSERT INTO meta(k,v) VALUES('library_synced_at',?) "
            "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (now,))
        conn.execute(
            "INSERT INTO meta(k,v) VALUES('library_index_mtime',?) "
            "ON CONFLICT(k) DO UPDATE SET v=excluded.v", (repr(mtime),))
        conn.commit()
    from .ingest import reresolve_all
    reresolve_all(conn)
    try:
        from .sources import refresh as refresh_sources
        refresh_sources(force=False, network=False)  # local scan only; no network in this path
    except Exception as e:
        print(f"[skillhub] source refresh skipped: {e}")
    return {"ok": True, "count": len(ids), "synced_at": now}


@router.post("/sync")
def sync():
    return sync_library()


@router.get("/status")
def status():
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM skills WHERE in_library=1").fetchone()["c"]
    synced = conn.execute("SELECT v FROM meta WHERE k='library_synced_at'").fetchone()
    return {"count": n, "index_path": settings.library_index,
            "synced_at": synced["v"] if synced else None}
