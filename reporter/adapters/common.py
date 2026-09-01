"""Shared helpers for reporter adapters. Stdlib only."""
import hashlib
import os
import re
import subprocess
from pathlib import Path

IGNORE_NAMES = {".git", ".DS_Store", "Thumbs.db", ".gitignore"}


def is_skill_dir(path: Path) -> bool:
    """A directory is a skill only when it holds a SKILL.md (case-insensitive).
    Without this check an entry dir's stray folders count as skills.
"""
    try:
        return any(c.name.lower() == "skill.md" and c.is_file() for c in path.iterdir())
    except OSError:
        return False


BLOCK_SCALARS = ("|", ">", "|-", ">-", "|+", ">+", "")


def read_frontmatter(skill_dir: Path) -> tuple[str, str]:
    """(name, description) from SKILL.md YAML frontmatter; ('','') when absent.

    Handles block scalars (`description: |` with the text on indented lines
    below) — a plain one-line regex captures only the pipe and silently drops
    every multi-line description, which is most of them.
    """
    for cand in ("SKILL.md", "skill.md"):
        p = skill_dir / cand
        if p.is_file():
            break
    else:
        return "", ""
    try:
        head = p.read_text(encoding="utf-8", errors="replace")[:4000]
    except OSError:
        return "", ""
    n = re.search(r"^name:\s*(.+)$", head, re.M)
    name = n.group(1).strip().strip("\"'") if n else ""

    desc = ""
    m = re.search(r"^description:[ \t]*(.*)$", head, re.M)
    if m:
        first = m.group(1).strip()
        if first in BLOCK_SCALARS:
            lines = []
            for line in head[m.end():].splitlines()[1:]:
                if line.strip() in ("---", "..."):
                    break
                if line.strip() and not line[:1].isspace():
                    break          # a non-indented line is the next key
                lines.append(line.strip())
            desc = " ".join(x for x in lines if x).strip()
        else:
            desc = first.strip("\"'")
    return name, desc


def hash_dir(path: Path, limit: int = 2_000_000) -> str:
    """Stable sha256 over a skill's relative paths + file bytes, so identical
    copies across tools hash alike and a drifted copy stands out."""
    h = hashlib.sha256()
    total = 0
    try:
        for root, dirs, files in os.walk(path, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in IGNORE_NAMES)
            rel_root = os.path.relpath(root, path)
            for f in sorted(files):
                if f in IGNORE_NAMES:
                    continue
                rel = os.path.normpath(os.path.join(rel_root, f))
                h.update(rel.encode("utf-8", "replace"))
                fp = os.path.join(root, f)
                try:
                    size = os.path.getsize(fp)
                    if total + size > limit:      # cap: hash the shape, not a huge blob
                        h.update(str(size).encode())
                        continue
                    with open(fp, "rb") as fh:
                        h.update(fh.read())
                    total += size
                except OSError:
                    h.update(b"<unreadable>")
    except OSError:
        return ""
    return h.hexdigest()


def git_tracked_names(path: Path) -> set[str] | None:
    """Top-level names under `path` that the enclosing repo tracks, or None when
    `path` is not inside a repo.

    An entity skill inside a cloned repo is not a stray copy someone made — it
    shipped with the project, and updating it means pulling that repo. Telling
    the two apart is the difference between a real finding and noise. One call
    per entry directory, not per skill.
    """
    try:
        p = subprocess.run(
            ["git", "-C", str(path), "ls-files", "-z"],
            capture_output=True, timeout=30,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    except (OSError, subprocess.TimeoutExpired):
        return None
    if p.returncode != 0:
        return None
    out: set[str] = set()
    for raw in p.stdout.split(b"\0"):
        if raw:
            out.add(raw.decode("utf-8", "replace").split("/")[0])
    return out


def target_tree_present(target: str) -> bool:
    """True when the directory the target should sit in still exists.

    A symlink whose target is unreachable means one of two very different
    things, and telling them apart is what keeps the broken-link count worth
    looking at:

      · the skill was renamed or deleted — the directory it lived in is still
        there, so the absence is about this one entry
      · the whole tree is not mounted — the library is a NAS share over SMB,
        and unplugging it takes 91 symlinks with it at once (measured), which
        would run the dashboard's only red indicator from 56 to 147 and bury
        the genuinely stale ones, precisely when the real answer is "come back
        when the NAS is up"

    Only the first is a broken link. Stale means the path is gone *while its parent tree remains* —
    a whole absent tree is an unmounted volume, not a broken link.

    `os.path.isdir` swallows OSError and returns False, so an unreachable
    network path lands on the not-present side, which is the safe side.
    """
    return os.path.isdir(os.path.dirname(os.path.abspath(target)))


def scan_entry_dir(path: Path, agent: str, scope: str, project_path: str = "",
                   shared_with: str = "") -> list[dict]:
    """List skill entries in one entry dir: symlinks (resolved), entity dirs,
    broken links. Non-skill directories and plain files are ignored."""
    items: list[dict] = []
    if not path.is_dir():
        return items
    try:
        children = sorted(path.iterdir())
    except PermissionError:
        raise  # caller must degrade to snapshot=False, not claim completeness
    except OSError:
        return items
    tracked = git_tracked_names(path)
    for child in children:
        name = child.name
        if name.startswith(".") or name in IGNORE_NAMES:
            continue
        target = os.path.realpath(child)
        if child.is_symlink():
            try:
                os.stat(target)
                link_type = "symlink"
            except FileNotFoundError:
                # gone, but only call it broken if the tree it lived in is
                # still there; otherwise the volume is simply not mounted
                link_type = "broken" if target_tree_present(target) else "unrooted"
            except OSError:
                # unverifiable (e.g. TCC-denied network volume in a launchd
                # context) — report as symlink, not broken
                link_type = "symlink"
        elif child.is_dir():
            # A child under a symlinked entry dir (e.g. ~/.agents/skills -> the
            # library) physically lives at the source: it is that source, not a
            # local copy, so it must not be reported as an unmanaged entity.
            link_type = "entity" if target == os.path.abspath(child) else "symlink"
            if link_type == "entity":
                target = ""
        else:
            continue
        if link_type not in ("broken", "unrooted") and not is_skill_dir(child):
            continue
        item = {
            "agent": agent, "scope": scope, "project_path": project_path,
            "entry_name": name, "entry_path": str(child),
            "link_type": link_type, "target_path": target,
            "shared_with": shared_with,
        }
        if link_type == "entity":
            # only entities can drift; a symlink is the library file itself
            item["content_hash"] = hash_dir(child)
            nm, desc = read_frontmatter(child)
            item["skill_name"], item["skill_desc"] = nm, desc
            item["vcs"] = ("vendored" if tracked is not None and name in tracked
                           else "loose" if tracked is None
                           else "untracked")
        items.append(item)
    return items


def read_new_bytes(path: Path, offset: int) -> tuple[bytes, int]:
    """Read complete new lines beyond `offset`. Returns (chunk, new_offset);
    a trailing partial line is left for the next run."""
    try:
        size = path.stat().st_size
    except OSError:
        return b"", offset
    if size < offset:      # truncated/rotated — reparse from scratch
        offset = 0
    if size == offset:
        return b"", offset
    with open(path, "rb") as fh:
        fh.seek(offset)
        data = fh.read()
    end = data.rfind(b"\n")
    if end == -1:
        return b"", offset
    return data[:end + 1], offset + end + 1
