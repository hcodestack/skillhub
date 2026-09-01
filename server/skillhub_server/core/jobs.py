"""Last-run status for the hub's unattended work.

Three jobs run with nobody watching: the library sync, the upstream check and
the safety scan. They reported only to stdout, so a failure left the dashboard
showing stale numbers with nothing to say they were stale — which is the quiet
failure this project exists to catch, happening inside the project itself.

The start is written before the work begins, so a job that hangs or dies with
the process reads as "running since ..." rather than simply going missing.
"""
import time
from contextlib import contextmanager

from .db import get_conn, tx
from .i18n import tr

# order is the order they are shown in; the value is a message key, resolved
# per request so the health page and the exported report follow the language
JOBS: dict[str, str] = {
    "library_sync": "job.library_sync",
    "upstream_check": "job.upstream_check",
    "vetting_scan": "job.vetting_scan",
}

# the built-in self-reporter joins the board only when it is actually enabled,
# so container deployments don't show a permanently-"never" row
from .config import settings as _settings
if _settings.self_report_enabled():
    JOBS["self_report"] = "job.self_report"

STUCK_AFTER = 30 * 60   # a run still unfinished after this long is not merely slow


def _write(job: str, started: int, finished: int, ok: int,
           detail: str, error: str) -> None:
    conn = get_conn()
    with tx():
        conn.execute(
            "INSERT INTO job_runs(job,started_at,finished_at,ok,detail,error) "
            "VALUES(?,?,?,?,?,?) ON CONFLICT(job) DO UPDATE SET "
            "started_at=excluded.started_at, finished_at=excluded.finished_at, "
            "ok=excluded.ok, detail=excluded.detail, error=excluded.error",
            (job, started, finished, ok, detail[:300], error[:500]))
        conn.commit()


class Run:
    """Handle yielded by `record`; the job sets what it wants reported."""

    def __init__(self) -> None:
        self.detail = ""
        self.ok = True      # set False for a failure the job handled itself


@contextmanager
def record(job: str):
    started = int(time.time())
    _write(job, started, 0, 0, "", "")
    run = Run()
    try:
        yield run
    except Exception as e:
        # recorded, then re-raised: whatever the caller already does about
        # errors keeps doing it
        _write(job, started, int(time.time()), 0, run.detail,
               f"{type(e).__name__}: {e}")
        raise
    _write(job, started, int(time.time()), 1 if run.ok else 0,
           run.detail, "" if run.ok else run.detail)


def last_runs(lang: str = "en") -> list[dict]:
    """One row per known job, including jobs that have never run."""
    rows = {r["job"]: r for r in get_conn().execute("SELECT * FROM job_runs")}
    now = int(time.time())
    out = []
    for job, key in JOBS.items():
        label = tr(lang, key)
        r = rows.get(job)
        if r is None:
            out.append({"job": job, "label": label, "status": "never",
                        "started_at": 0, "finished_at": 0, "duration_s": 0,
                        "detail": "", "error": ""})
            continue
        if not r["finished_at"]:
            running_for = now - r["started_at"]
            status = "stuck" if running_for > STUCK_AFTER else "running"
            duration = running_for
        else:
            status = "ok" if r["ok"] else "failed"
            duration = r["finished_at"] - r["started_at"]
        out.append({"job": job, "label": label, "status": status,
                    "started_at": r["started_at"], "finished_at": r["finished_at"],
                    "duration_s": duration, "detail": r["detail"] or "",
                    "error": r["error"] or ""})
    return out
