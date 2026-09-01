"""Resolution: map raw skill keys and symlink targets to library skill ids."""
import os
import sqlite3

from .config import settings

# When several skills share a basename, an ambiguous key resolves to the
# earliest source class here; labels come from the index file when one is
# used ("library" is what self-scan assigns). Unknown labels rank last.
SOURCE_PRIORITY = {"self-made": 0, "own": 0, "organized": 1, "library": 2,
                   "installer": 3}


def _prefixes(rel: str) -> list[str]:
    """Longest-first candidate ids from a path relative to a library base."""
    parts = [p for p in rel.strip("/").split("/") if p]
    return ["/".join(parts[:n]) for n in range(len(parts), 0, -1)]


def target_to_id(target_path: str, library_root: str,
                 known: set | None = None) -> str | None:
    """Resolve an absolute (realpath'd) symlink target inside the library to a
    skill id.

    Reporters send targets in their OWN mount view (e.g. /Volumes/...), while
    the hub may see the library elsewhere (Docker: /library) — so after trying
    the configured bases, fall back to matching a base's final path segment
    anywhere in the target. With `known`, the longest candidate prefix that is
    a real id wins (a file deep inside a skill still resolves to the skill);
    without it, the full relative path is the id."""
    if not target_path:
        return None
    bases = settings.library_bases() or ([library_root] if library_root else [])
    rel = ""
    for base in bases:
        b = base.rstrip("/") + "/"
        if target_path.startswith(b):
            rel = target_path[len(b):]
            break
    if not rel:
        for base in bases:
            marker = "/" + os.path.basename(base.rstrip("/")) + "/"
            i = target_path.find(marker)
            if i != -1:
                rel = target_path[i + len(marker):]
                break
    if not rel:
        return None
    cands = _prefixes(rel)
    if known:
        for c in cands:
            if c in known:
                return c
    return cands[0] if cands else None


def build_key_maps(conn: sqlite3.Connection):
    """Returns (exact ids set, basename -> [ids], id -> source)."""
    rows = conn.execute("SELECT id, source FROM skills WHERE in_library=1").fetchall()
    exact = {r["id"] for r in rows}
    source_of = {r["id"]: r["source"] for r in rows}
    by_base: dict[str, list[str]] = {}
    for r in rows:
        by_base.setdefault(r["id"].split("/")[-1].lower(), []).append(r["id"])
    return exact, by_base, source_of


def resolve_key(key: str, exact: set, by_base: dict, source_of: dict,
                conn: sqlite3.Connection | None = None) -> tuple[str | None, str]:
    """Resolve a raw invocation key ('docx', 'vendor/skill', 'plugin:skill').
    Returns (skill_id | None, note)."""
    if not key:
        return None, ""
    if key in exact:
        return key, ""
    cands = by_base.get(key.split("/")[-1].lower(), [])
    if len(cands) == 1:
        return cands[0], ""
    if len(cands) > 1:
        # prefer a candidate that is actually loaded somewhere under this entry name
        if conn is not None:
            ph = ",".join("?" * len(cands))
            row = conn.execute(
                f"SELECT skill_id FROM installs WHERE active=1 AND skill_id IN ({ph}) "
                "AND entry_name=? LIMIT 1", (*cands, key.split("/")[-1])).fetchone()
            if row and row["skill_id"]:
                return row["skill_id"], "ambiguous:install-preferred"
        cands = sorted(cands, key=lambda i: (SOURCE_PRIORITY.get(source_of.get(i, ""), 9), i))
        return cands[0], "ambiguous"
    return None, ""
