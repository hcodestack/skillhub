"""Codex adapter.

Usage signal: rollout JSONL lines where a function_call reads a SKILL.md —
Codex loads a skill by reading its SKILL.md, so that read is the invocation
marker. Inventory: ~/.codex/skills (global entries)."""
import hashlib
import re
from pathlib import Path

from . import common

AGENT = "codex"
ROOT = Path.home() / ".codex"

_PATH_RE = re.compile(r'([\w\-./~@]+/SKILL\.md)')
_TS_RE = re.compile(r'"timestamp"\s*:\s*"([^"]{10,40})"')
_FNAME_TS_RE = re.compile(r'rollout-(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})')


def _file_ts(path: Path) -> str:
    m = _FNAME_TS_RE.search(path.name)
    if not m:
        return ""
    d, t = m.group(1).split("T")
    return f"{d}T{t.replace('-', ':')}"


def _parse_chunk(chunk: bytes, path: Path, base_offset: int) -> list[dict]:
    events = []
    fallback_ts = _file_ts(path)
    offset = base_offset
    for raw in chunk.splitlines():
        line_offset = offset
        offset += len(raw) + 1
        if b"SKILL.md" not in raw or b"function_call" not in raw:
            continue
        text = raw.decode("utf-8", errors="replace")
        tsm = _TS_RE.search(text)
        ts = (tsm.group(1)[:19] if tsm else fallback_ts)
        for p in dict.fromkeys(_PATH_RE.findall(text)):   # dedupe, keep order
            parts = p.split("/")
            if len(parts) < 2:
                continue
            key = parts[-2]
            events.append({
                "agent": AGENT, "skill_key": key,
                "ts": ts, "project": "",
                "session_id": path.stem,
                "source": "rollout",
                "hash": hashlib.sha1(
                    f"cx|{path.name}|{line_offset}|{key}".encode()).hexdigest(),
            })
    return events


def collect(state: dict) -> dict:
    files_state = state.setdefault("files", {})
    events: list[dict] = []

    sessions = ROOT / "sessions"
    if sessions.is_dir():
        for f in sorted(sessions.rglob("*.jsonl")):
            fp = str(f)
            st = files_state.get(fp) or {}
            offset = st.get("offset", 0)
            chunk, new_offset = common.read_new_bytes(f, offset)
            if chunk and b"SKILL.md" in chunk:
                events += _parse_chunk(chunk, f, offset)
            files_state[fp] = {"offset": new_offset}

    # inventory is collected centrally by adapters/tools.py
    return {"inventory": [], "events": events, "snapshot": True}
