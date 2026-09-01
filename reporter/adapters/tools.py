"""Generic inventory scanner — walks every installed AI coding tool's skills
directory, global and per project.

Previously only claude-code / codex / workbuddy were scanned, so skills loaded
into Cursor, Gemini CLI, Copilot, Qoder, Trae ... were invisible. The directory
table lives in tool_table.py.

One physical directory can serve several tools (project `.agents/skills` serves
nine). Each directory is scanned once, attributed to a canonical agent key, and
carries the other tools' names in `shared_with` — attributing a shared dir to
every tool would multiply the same entry N times.
"""
from pathlib import Path

from . import common
from .tool_table import DETECT_DIR, GLOBAL_DIR, NAME, PROJECT_DIR, TOOLS  # noqa: F401

HOME = Path.home()


def installed_tools() -> list[str]:
    """Tool keys whose detect dir exists under $HOME."""
    return [k for k, t in TOOLS.items() if (HOME / t[DETECT_DIR]).is_dir()]


def _canonical(dirs: dict[str, list[str]]) -> list[tuple[str, str, str]]:
    """(dir, agent_key, shared_with).

    A directory used by exactly one tool is attributed to that tool. A directory
    several tools read (project `.agents/skills` serves nine) belongs to none of
    them, so it gets a synthetic `shared:<dir>` key — naming one arbitrary tool
    as the owner would misreport who loaded the skill."""
    out = []
    for d, keys in sorted(dirs.items()):
        if len(keys) == 1:
            out.append((d, keys[0], ""))
        else:
            out.append((d, f"shared:{d}", ", ".join(TOOLS[k][NAME] for k in keys)))
    return out


def collect(state: dict, project_roots: list[str] | None = None) -> dict:
    keys = installed_tools()
    inventory: list[dict] = []
    snapshot = True
    # Every agent key we actually scanned under — including the synthetic
    # shared:<dir> keys _canonical() mints for multi-tool directories. The
    # hub's deactivation sweep matches rows by this list, and shared keys
    # used to be missing from it: an entry deleted from a shared directory
    # stayed active on the dashboard forever (found the hard way: entries
    # deleted from a shared directory refused to disappear from the dashboard).
    scanned: set[str] = set()

    global_dirs: dict[str, list[str]] = {}
    for k in keys:
        global_dirs.setdefault(TOOLS[k][GLOBAL_DIR], []).append(k)
    for rel, key, shared in _canonical(global_dirs):
        scanned.add(key)
        try:
            inventory += common.scan_entry_dir(HOME / rel, key, "global", "", shared)
        except PermissionError:
            snapshot = False

    for root in sorted(set(project_roots or [])):
        rootp = Path(root)
        if _same_dir(rootp, HOME):
            continue  # a session run from $HOME would re-scan the global dirs
        if not rootp.is_dir():
            # missing on an unreachable volume = unknown, not removed
            if _unverifiable(root):
                snapshot = False
            continue
        project_dirs: dict[str, list[str]] = {}
        for k in keys:
            rel = TOOLS[k][PROJECT_DIR]
            if rel:
                project_dirs.setdefault(rel, []).append(k)
        for rel, key, shared in _canonical(project_dirs):
            scanned.add(key)
            d = rootp / rel
            try:
                inventory += common.scan_entry_dir(d, key, "project", root, shared)
            except PermissionError:
                snapshot = False

    # keys ∪ scanned: shared directories replace their tools' own keys in the
    # scan, but rows written under a tool's own name by older reporter versions
    # must keep participating in deactivation too.
    return {"inventory": inventory, "events": [], "snapshot": snapshot,
            "agents": sorted(set(keys) | scanned)}


def _same_dir(a: Path, b: Path) -> bool:
    try:
        return a.exists() and b.exists() and a.resolve() == b.resolve()
    except OSError:
        return False


def _unverifiable(cwd: str) -> bool:
    parts = Path(cwd).parts
    if len(parts) >= 3 and parts[0] == "/" and parts[1] == "Volumes":
        try:
            return not Path(*parts[:3]).is_dir()
        except OSError:
            return True
    return False
