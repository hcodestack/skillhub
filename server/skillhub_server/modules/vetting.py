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
from ..core.i18n import tr
from ..core.jobs import record
from ..core.vetting import RULE_CATEGORY, SEVERITY_ORDER, scan_dir, skill_dir

router = APIRouter(prefix="/vetting", tags=["vetting"])


def rescan(only_missing: bool = False) -> dict:
    """Wrapper so the run is recorded whether it came from startup or a POST."""
    with record("vetting_scan") as run:
        res = _rescan(only_missing=only_missing)
        # job details are written once and read in whatever language the reader
        # picks later, so they are stored in English
        mode = tr("en", "job.mode.incremental" if only_missing else "job.mode.full")
        # the startup pass is incremental, so a healthy run normally scans
        # nothing at all — reported as "0 scanned / 0 flagged", which reads like
        # a failure: exactly the misreading this whole section exists to prevent
        run.detail = (
            tr("en", "job.detail.vetting", mode=mode,
               scanned=res["scanned"], flagged=res["flagged"])
            if res["scanned"] else tr("en", "job.detail.vettingIdle", mode=mode))
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


def localize(findings: list[dict], lang: str) -> list[dict]:
    """Category and rationale are derived from the rule id, not from what was
    stored — so switching language needs no rescan, and a rule whose wording is
    reworded takes effect on the next read."""
    out = []
    for f in findings:
        rid = f.get("rule", "")
        cat = RULE_CATEGORY.get(rid)
        out.append({**f,
                    "category": tr(lang, cat) if cat else f.get("category", ""),
                    "description": tr(lang, f"vet.rule.{rid}") if rid
                    else f.get("description", "")})
    return out


def findings_map(lang: str = "en") -> dict[str, dict]:
    conn = get_conn()
    out: dict[str, dict] = {}
    for r in conn.execute("SELECT * FROM skill_vetting WHERE count > 0").fetchall():
        out[r["skill_id"]] = {
            "count": r["count"], "top_severity": r["top_severity"],
            "findings": localize(json.loads(r["findings"] or "[]"), lang),
            "scanned_at": r["scanned_at"],
        }
    return out


@router.get("")
def list_findings(lang: str = "en"):
    conn = get_conn()
    names = {r["id"]: (r["name"] or r["id"]) for r in
             conn.execute("SELECT id, name FROM skills").fetchall()}
    items = [{"skill_id": k, "name": names.get(k, k), **v}
             for k, v in findings_map(lang).items()]
    items.sort(key=lambda x: (SEVERITY_ORDER.get(x["top_severity"], 9),
                              -x["count"], x["skill_id"]))
    total = conn.execute("SELECT COUNT(*) c FROM skill_vetting").fetchone()["c"]
    return {"items": items, "scanned": total,
            "library_total": conn.execute(
                "SELECT COUNT(*) c FROM skills WHERE in_library=1").fetchone()["c"]}


@router.post("/scan")
def scan(only_missing: bool = False):
    return rescan(only_missing=only_missing)
