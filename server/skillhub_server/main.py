"""Skillhub server entrypoint."""
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .core.config import settings
from .core.db import get_conn
from .modules import get_routers
from .modules.library import sync_library


def _check_upstreams_bg() -> None:
    """Upstream checks run off the startup path so a slow network never delays
    the hub from serving."""
    try:
        from .modules.sources import refresh as refresh_sources
        res = refresh_sources(force=False, network=True)
        print(f"[skillhub] upstream check: {res}")
    except Exception as e:
        print(f"[skillhub] upstream check failed: {e}")


SELF_REPORT_INTERVAL = 15 * 60


def _self_report_loop() -> None:
    """Single-machine mode: the server reports on itself, so nobody has to set
    up launchd/cron just to see their own machine. Runs the bundled reporter
    as a subprocess against this server every 15 minutes; each run is recorded
    like any other background job, so a silent failure shows on the health
    page instead of quietly staling the data."""
    import subprocess
    import sys
    import time as _t

    from .core.jobs import record

    url = f"http://127.0.0.1:{settings.port}"
    _t.sleep(8)                       # let uvicorn start accepting first
    first = True
    while True:
        try:
            with record("self_report") as run:
                cmd = [sys.executable, settings.reporter_script,
                       "--server", url] + (["--backfill"] if first else [])
                res = subprocess.run(cmd, capture_output=True, text=True,
                                     timeout=10 * 60)
                out = (res.stdout or "").strip().splitlines()
                run.detail = out[-1][:200] if out else ""
                if res.returncode != 0:
                    run.ok = False
                    run.detail = (res.stderr or run.detail or "").strip()[:200]
        except Exception as e:
            print(f"[skillhub] self-report failed: {e}")
        first = False
        _t.sleep(SELF_REPORT_INTERVAL)


def _vet_skills_bg() -> None:
    """Reading every file of every skill is far too slow for a request, so the
    safety review runs here and serves cached results."""
    try:
        from .modules.vetting import rescan
        print(f"[skillhub] vetting: {rescan(only_missing=True)}")
    except Exception as e:
        print(f"[skillhub] vetting failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_conn()
    result = sync_library()
    if not result.get("ok"):
        print(f"[skillhub] library sync skipped: {result.get('error')}")
    threading.Thread(target=_check_upstreams_bg, daemon=True).start()
    threading.Thread(target=_vet_skills_bg, daemon=True).start()
    if settings.self_report_enabled():
        threading.Thread(target=_self_report_loop, daemon=True).start()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="Skillhub", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_methods=["*"], allow_headers=["*"],
    )
    for r in get_routers():
        app.include_router(r, prefix="/api/v1")

    static = Path(settings.static_dir)
    if static.is_dir():
        app.mount("/", StaticFiles(directory=str(static), html=True), name="web")
    return app


app = create_app()


def main():
    import uvicorn
    uvicorn.run("skillhub_server.main:app", host=settings.host, port=settings.port)


if __name__ == "__main__":
    main()
