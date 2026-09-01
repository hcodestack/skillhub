"""Vetting module — runs the deterministic safety review over library skills.

Scanning reads every file of every skill, so it never sits in a request path:
results are cached in SQLite and refreshed by a background pass, the same shape
as the upstream-update check.
"""
import json
import time

from fastapi import APIRouter

from ..core.config import settings
from ..core.db import get_conn, tx
from ..core.jobs import record
from ..core.vetting import SEVERITY_ORDER, scan_dir, skill_dir

router = APIRouter(prefix="/vetting", tags=["vetting"])


def rescan(only_missing: bool = False) -> dict:
    """Wrapper so the run is recorded whether it came from startup or a POST."""
    with record("vetting_scan") as run:
        res = _rescan(only_missing=only_missing)
        mode = "增量" if only_missing else "全量"
        # the startup pass is incremental, so a healthy run normally scans
        # nothing at all — reported as "0 扫描 / 0 命中" that reads like a
        # failure, which is the misreading this whole section exists to prevent
        run.detail = (f"{mode}：{res['scanned']} 扫描 / {res['flagged']} 命中"
                      if res["scanned"] else f"{mode}：无待扫描技能（结果均已缓存）")
        return res


def _rescan(only_missing: bool = False) -> dict:
    conn = get_conn()
    root = settings.library_root_path
    rows = conn.execute("SELECT id FROM skills WHERE in_library=1").fetchall()
    done = {r["skill_id"] for r in conn.execute(
        "SELECT skill_id FROM skill_vetting").fetchall()} if only_missing else set()
    now = int(time.time())
    scanned = 0
    flagged = 0
    for r in rows:
        sid = r["id"]
        if sid in done:
            continue
        d = skill_dir(root, sid)
        if not d:
            continue
        findings = scan_dir(d)
        scanned += 1
        if findings:
            flagged += 1
        top = findings[0]["severity"] if findings else ""
        with tx():
            conn.execute(
                "INSERT INTO skill_vetting(skill_id,findings,top_severity,count,scanned_at) "
                "VALUES(?,?,?,?,?) ON CONFLICT(skill_id) DO UPDATE SET "
                "findings=excluded.findings, top_severity=excluded.top_severity, "
                "count=excluded.count, scanned_at=excluded.scanned_at",
                (sid, json.dumps(findings, ensure_ascii=False), top,
                 len(findings), now))
            conn.commit()
    return {"ok": True, "scanned": scanned, "flagged": flagged}


def findings_map() -> dict[str, dict]:
    conn = get_conn()
    out: dict[str, dict] = {}
    for r in conn.execute("SELECT * FROM skill_vetting WHERE count > 0").fetchall():
        out[r["skill_id"]] = {
            "count": r["count"], "top_severity": r["top_severity"],
            "findings": json.loads(r["findings"] or "[]"),
            "scanned_at": r["scanned_at"],
        }
    return out


@router.get("")
def list_findings():
    conn = get_conn()
    names = {r["id"]: (r["name"] or r["id"]) for r in
             conn.execute("SELECT id, name FROM skills").fetchall()}
    items = [{"skill_id": k, "name": names.get(k, k), **v}
             for k, v in findings_map().items()]
    items.sort(key=lambda x: (SEVERITY_ORDER.get(x["top_severity"], 9),
                              -x["count"], x["skill_id"]))
    total = conn.execute("SELECT COUNT(*) c FROM skill_vetting").fetchone()["c"]
    return {"items": items, "scanned": total,
            "library_total": conn.execute(
                "SELECT COUNT(*) c FROM skills WHERE in_library=1").fetchone()["c"]}


@router.post("/scan")
def scan(only_missing: bool = False):
    return rescan(only_missing=only_missing)
