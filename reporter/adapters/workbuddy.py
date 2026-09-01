"""WorkBuddy adapter.

Usage: WorkBuddy maintains its own ~/.workbuddy/usage-log.json with per-skill
recent-use dates — day granularity, which is what it offers. Inventory:
~/.workbuddy/skills (these are entity dirs today, a governance blind spot)."""
import hashlib
import json
from pathlib import Path

from . import common

AGENT = "workbuddy"
ROOT = Path.home() / ".workbuddy"


def collect(state: dict) -> dict:
    events: list[dict] = []
    usage_log = ROOT / "usage-log.json"
    if usage_log.is_file():
        try:
            data = json.loads(usage_log.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            data = {}
        for key, rec in (data.get("skills") or {}).items():
            if not isinstance(rec, dict) or rec.get("type") != "skill":
                continue
            dates = set(rec.get("recentDates") or [])
            for extra in (rec.get("lastUsedDate"), rec.get("firstSeenDate")):
                if extra:
                    dates.add(extra)
            for d in sorted(dates):
                events.append({
                    "agent": AGENT, "skill_key": key,
                    "ts": f"{d}T12:00:00", "project": "",
                    "session_id": "", "source": "usage-log",
                    "hash": hashlib.sha1(f"wb|{key}|{d}".encode()).hexdigest(),
                })

    # inventory is collected centrally by adapters/tools.py
    return {"inventory": [], "events": events, "snapshot": True}
