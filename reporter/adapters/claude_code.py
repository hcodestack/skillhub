"""Claude Code adapter.

Usage events: Skill tool invocations recorded in ~/.claude/projects/**/*.jsonl
(incremental, byte-offset cursor per file). Inventory: ~/.claude/skills plus
each known project's .claude/skills (projects discovered from transcript cwd)."""
import hashlib
import json
from pathlib import Path

from . import common

AGENT = "claude-code"
ROOT = Path.home() / ".claude"


def _cwd_unverifiable(cwd: str) -> bool:
    """A missing cwd on a fixed disk means the project was deleted; a missing
    cwd whose /Volumes/<vol> root is itself unreachable means the volume is
    unmounted or TCC-hidden — its state is unknown, not removed."""
    parts = Path(cwd).parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "Volumes":
        try:
            return not Path(*parts[:3]).is_dir()
        except OSError:
            return True
    return False


def _peek_cwd(path: Path) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            head = f.read(16384)
    except OSError:
        return ""
    i = head.find('"cwd":"')
    if i == -1:
        return ""
    j = head.find('"', i + 7)
    return head[i + 7:j] if j != -1 else ""


def _parse_chunk(chunk: bytes, path: Path) -> tuple[list[dict], str]:
    events, cwd = [], ""
    for raw in chunk.splitlines():
        if b'"Skill"' not in raw:
            continue
        try:
            obj = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if obj.get("type") != "assistant":
            continue
        content = (obj.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not (isinstance(block, dict) and block.get("type") == "tool_use"
                    and block.get("name") == "Skill"):
                continue
            key = ((block.get("input") or {}).get("skill") or "").strip()
            if not key:
                continue
            cwd = cwd or obj.get("cwd") or ""
            uid = block.get("id") or obj.get("uuid") or f"{path.name}:{len(events)}"
            events.append({
                "agent": AGENT, "skill_key": key,
                "ts": (obj.get("timestamp") or "")[:19],
                "project": obj.get("cwd") or "",
                "session_id": obj.get("sessionId") or path.stem,
                "source": "transcript",
                "hash": hashlib.sha1(f"cc|{uid}|{key}".encode()).hexdigest(),
            })
    return events, cwd


def collect(state: dict) -> dict:
    files_state = state.setdefault("files", {})
    events: list[dict] = []
    cwds: set[str] = set()

    projects = ROOT / "projects"
    if projects.is_dir():
        for f in sorted(projects.glob("*/*.jsonl")):
            fp = str(f)
            st = files_state.get(fp) or {}
            chunk, new_offset = common.read_new_bytes(f, st.get("offset", 0))
            cwd = st.get("cwd") or ""
            if chunk:
                evs, seen_cwd = _parse_chunk(chunk, f)
                events += evs
                cwd = cwd or seen_cwd
            cwd = cwd or _peek_cwd(f)
            files_state[fp] = {"offset": new_offset, "cwd": cwd}
            if cwd:
                cwds.add(cwd)

    # Inventory for every tool (including this one) is collected by
    # adapters/tools.py; here we only surface events and the project roots it
    # needs. cwds come from transcripts, so they are the known project list.
    return {"inventory": [], "events": events, "snapshot": True,
            "project_roots": sorted(cwds)}
