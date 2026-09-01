"""Sources module — where a library skill came from, and whether its upstream
has moved on.

Provenance available today, in descending confidence:
  1. the skill dir is a git checkout  -> remote URL + local commit are exact,
     and `git ls-remote` tells us the upstream head without fetching
  2. the skill lives under the declared installer subdirectory -> its installer owns updates
  3. anything else -> origin unknown; recorded as such rather than guessed

Reads only: remote URL and local HEAD are parsed straight out of `.git` files,
so nothing writes to the library (the hub mounts it read-only by design).
"""
import configparser
import os
import re
import subprocess
import time
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from ..core.config import settings
from ..core.provenance import lookup as provenance_lookup
from ..core.db import get_conn, tx
from ..core.jobs import record

router = APIRouter(prefix="/sources", tags=["sources"])

CHECK_TTL = 6 * 3600          # re-check upstream at most this often
LS_REMOTE_TIMEOUT = 20


def _read_head(git_dir: Path) -> str:
    """Local HEAD commit, parsed from files (no subprocess, no lock, no write)."""
    try:
        head = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    if not head.startswith("ref:"):
        return head                      # detached HEAD is the sha itself
    ref = head[4:].strip()
    try:
        return (git_dir / ref).read_text(encoding="utf-8").strip()
    except OSError:
        pass
    try:                                  # packed-refs fallback
        for line in (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines():
            if line.endswith(" " + ref):
                return line.split(" ", 1)[0]
    except OSError:
        pass
    return ""


def _read_origin(git_dir: Path) -> str:
    cfg = configparser.ConfigParser()
    try:
        cfg.read(git_dir / "config")
    except (OSError, configparser.Error):
        return ""
    for section in cfg.sections():
        if section.replace('"', "").strip() == 'remote origin':
            return cfg[section].get("url", "").strip()
    return ""


def scan_sources() -> dict[str, dict]:
    """{skill_id: {kind, origin, local_ref, path}} for everything we can trace."""
    conn = get_conn()
    known = [r["id"] for r in conn.execute(
        "SELECT id FROM skills WHERE in_library=1").fetchall()]
    found: dict[str, dict] = {}

    for base_s in settings.library_bases():
        base = Path(base_s)
        if not base.is_dir():
            continue
        for depth in (1, 2, 3):
            for d in base.glob("/".join(["*"] * depth)):
                git_dir = d / ".git"
                if not git_dir.is_dir():
                    continue
                origin, local = _read_origin(git_dir), _read_head(git_dir)
                if not origin:
                    continue
                rid = str(d.relative_to(base)).replace("\\", "/")
                # a repo above skill level covers every skill beneath it
                for sid in known:
                    if sid == rid or sid.startswith(rid + "/"):
                        found[sid] = {"kind": "git", "origin": origin,
                                      "local_ref": local, "path": str(d)}

    # recorded provenance for skills that are not git checkouts
    for sid in known:
        if sid in found:
            continue
        rec = provenance_lookup(sid)
        if not rec:
            continue
        origin, kind, conf, subpath, ev = rec
        found[sid] = {"kind": kind, "origin": origin, "local_ref": "",
                      "path": "", "confidence": conf, "subpath": subpath,
                      "evidence": ev}

    # a subdirectory owned by an installer CLI, if the deployment declares one
    if settings.installer_subdir:
        inst = Path(settings.library_root_path) / settings.installer_subdir
        if inst.is_dir():
            for d in inst.iterdir():
                if not d.is_dir() or d.name.startswith("."):
                    continue
                for sid in known:
                    if sid == d.name or sid.endswith("/" + d.name):
                        found.setdefault(sid, {
                            "kind": "installer", "origin": "", "local_ref": "",
                            "path": str(d)})
    return found


def _ls_remote(url: str) -> tuple[str, str]:
    """(upstream_sha, error). Needs no local repo, writes nothing."""
    if not re.match(r"^(https://|git@|ssh://)", url):
        return "", "unsupported url"
    try:
        p = subprocess.run(["git", "ls-remote", url, "HEAD"],
                           capture_output=True, text=True,
                           timeout=LS_REMOTE_TIMEOUT,
                           env={**os.environ, "GIT_TERMINAL_PROMPT": "0"})
    except FileNotFoundError:
        return "", "git not installed in this container"
    except subprocess.TimeoutExpired:
        return "", "timeout"
    if p.returncode != 0:
        return "", (p.stderr or "ls-remote failed").strip().splitlines()[-1][:200]
    out = p.stdout.split("\t")[0].strip() if p.stdout else ""
    return out, "" if out else "no HEAD on remote"


def refresh(force: bool = False, network: bool = True) -> dict:
    """Rescan local provenance; `network=False` skips upstream checks entirely.

    Upstream checks are network calls, so they must never sit in a request or
    startup path — a slow or unreachable GitHub would stall the whole hub."""
    if not network:
        # sync_library() calls this for a local-only provenance rescan. That is
        # not the upstream check, and recording it would let the dashboard claim
        # upstreams were checked when nothing left the machine.
        return _refresh(force, network)
    with record("upstream_check") as run:
        res = _refresh(force, network)
        run.detail = (f"{res['traced']} 溯源 / {res['checked']} 联网核对 / "
                      f"{res['cached']} 用缓存")
        return res


def _refresh(force: bool = False, network: bool = True) -> dict:
    conn = get_conn()
    now = int(time.time())
    sources = scan_sources()
    cached = {r["skill_id"]: dict(r) for r in
              conn.execute("SELECT * FROM skill_sources").fetchall()}
    checked = skipped = 0
    # one upstream repo commonly backs many skills — resolve each URL once
    # per run, not once per skill
    per_url: dict[str, tuple[str, str]] = {}

    with tx():
        for sid, s in sources.items():
            prev = cached.get(sid, {})
            remote, err = prev.get("remote_ref", ""), prev.get("last_error", "")
            age = now - int(prev.get("checked_at") or 0)
            did_check = False
            if network and s["kind"] in ("git", "catalog") and (
                    force or age > CHECK_TTL or prev.get("origin") != s["origin"]):
                if s["origin"] not in per_url:
                    per_url[s["origin"]] = _ls_remote(s["origin"])
                    checked += 1
                remote, err = per_url[s["origin"]]
                did_check = True
            else:
                skipped += 1
            baseline = prev.get("baseline_ref") or (remote if s["kind"] == "catalog" else "")
            conn.execute(
                "INSERT INTO skill_sources(skill_id,kind,origin,local_ref,remote_ref,"
                "path,checked_at,last_error,confidence,subpath,evidence,baseline_ref) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(skill_id) DO UPDATE SET kind=excluded.kind, "
                "origin=excluded.origin, local_ref=excluded.local_ref, "
                "remote_ref=excluded.remote_ref, path=excluded.path, "
                "checked_at=excluded.checked_at, last_error=excluded.last_error, "
                "confidence=excluded.confidence, subpath=excluded.subpath, "
                "evidence=excluded.evidence, baseline_ref=excluded.baseline_ref",
                # only an actual upstream call may advance checked_at: a local-only
                # scan that stamped it would make the next network check think it was fresh
                (sid, s["kind"], s["origin"], s["local_ref"], remote, s["path"],
                 now if did_check else (prev.get("checked_at") or 0),
                 err, s.get("confidence", ""), s.get("subpath", ""),
                 s.get("evidence", ""), baseline))
        if sources:
            ph = ",".join("?" * len(sources))
            conn.execute(f"DELETE FROM skill_sources WHERE skill_id NOT IN ({ph})",
                         tuple(sources))
        conn.commit()
    return {"ok": True, "traced": len(sources), "checked": checked, "cached": skipped}


def state_of(row) -> str:
    if row["kind"] == "installer":
        return "installer"
    if row["last_error"]:
        return "error"
    if row["kind"] == "catalog":
        # the local copy carries no commit of its own, so we can only report
        # whether the upstream repo moved since we first recorded it
        if not row["remote_ref"]:
            return "unknown"
        base = row["baseline_ref"] or ""
        return "moved" if base and base != row["remote_ref"] else "tracked"
    if not row["local_ref"] or not row["remote_ref"]:
        return "unknown"
    return "current" if row["local_ref"] == row["remote_ref"] else "behind"


def _update_cmd(row) -> str:
    """A command the user can actually paste — rewritten from the hub's mount
    point to the library path as they see it."""
    if row["kind"] == "installer":
        return "lark-cli update"
    if row["kind"] != "git" or state_of(row) != "behind":
        return ""
    path = row["path"] or ""
    root, display = settings.library_root_path, settings.library_display_path
    if root != display and path.startswith(root):
        path = display + path[len(root):]
    return f'git -C "{path}" pull --ff-only'


def status_map() -> dict[str, dict]:
    conn = get_conn()
    out = {}
    for r in conn.execute("SELECT * FROM skill_sources").fetchall():
        out[r["skill_id"]] = {
            "kind": r["kind"], "origin": r["origin"], "state": state_of(r),
            "local_ref": (r["local_ref"] or "")[:12],
            "remote_ref": (r["remote_ref"] or "")[:12],
            "checked_at": r["checked_at"], "error": r["last_error"],
            "confidence": r["confidence"], "subpath": r["subpath"],
            "evidence": r["evidence"],
            "update_cmd": _update_cmd(r),
        }
    return out


def _git(args: list[str], cwd: str | None = None, timeout: int = 120):
    """git with prompts disabled, ownership checks relaxed (the library is owned
    by the NAS user while this container runs as root), and file-mode tracking
    off — an SMB/NAS mount reports every file as 100755, which would otherwise
    make every repo look permanently dirty and block all updates."""
    return subprocess.run(
        ["git", "-c", "safe.directory=*", "-c", "core.fileMode=false", *args],
        cwd=cwd, capture_output=True, text=True, timeout=timeout,
        env={**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "true"})


class UpdateReq(BaseModel):
    skill_id: str


@router.post("/update")
def update(req: UpdateReq):
    """Fast-forward one git-backed skill to its upstream.

    Deliberately narrow: git checkouts only, --ff-only (never a merge commit),
    and refused outright when the working tree has local edits — a modified
    skill in the library is someone's work, not something to overwrite.
    Installer-managed skills are left to their own installer.
    """
    conn = get_conn()
    row = conn.execute("SELECT * FROM skill_sources WHERE skill_id=?",
                       (req.skill_id,)).fetchone()
    if not row:
        return {"ok": False, "error": "该技能没有可追溯的上游来源"}
    if row["kind"] != "git":
        return {"ok": False, "error": f"{row['kind']} 类技能由其安装器更新，hub 不代劳"}

    path = os.path.realpath(row["path"])
    lib = os.path.realpath(settings.library_root_path)
    if not path.startswith(lib + os.sep):
        return {"ok": False, "error": "目标路径不在技能库内，已拒绝"}
    if not os.path.isdir(os.path.join(path, ".git")):
        return {"ok": False, "error": "目标已不是 git 仓库"}

    st = _git(["status", "--porcelain"], cwd=path, timeout=60)
    if st.returncode != 0:
        return {"ok": False, "error": f"git status 失败：{st.stderr.strip()[:200]}"}
    if st.stdout.strip():
        n = len(st.stdout.strip().splitlines())
        return {"ok": False, "error": f"工作区有 {n} 处未提交改动，拒绝更新（避免覆盖你的修改）"}

    before = _read_head(Path(path) / ".git")
    pull = _git(["pull", "--ff-only"], cwd=path)
    if pull.returncode != 0:
        return {"ok": False, "error": (pull.stderr or pull.stdout).strip()[-300:]}
    after = _read_head(Path(path) / ".git")

    now = int(time.time())
    with tx():
        conn.execute("UPDATE skill_sources SET local_ref=?, remote_ref=?, "
                     "checked_at=?, last_error='' WHERE path=?",
                     (after, after, now, row["path"]))
        conn.commit()
    return {"ok": True, "skill_id": req.skill_id,
            "from": before[:12], "to": after[:12],
            "changed": before != after,
            "note": ("技能内容已变，建议在有库访问权的机器上跑 `skill index` "
                     "刷新目录（名称/描述可能已更新）") if before != after else "",
            "output": pull.stdout.strip()[-500:]}


@router.get("")
def list_sources():
    conn = get_conn()
    names = {r["id"]: (r["name"] or r["id"]) for r in
             conn.execute("SELECT id, name FROM skills").fetchall()}
    items = [{"skill_id": k, "name": names.get(k, k), **v}
             for k, v in status_map().items()]
    order = {"behind": 0, "moved": 1, "error": 2, "unknown": 3,
             "installer": 4, "tracked": 5, "current": 6}
    items.sort(key=lambda x: (order.get(x["state"], 9), x["skill_id"]))
    total = conn.execute(
        "SELECT COUNT(*) c FROM skills WHERE in_library=1").fetchone()["c"]
    return {"items": items, "library_total": total, "untraced": total - len(items)}


@router.post("/check")
def check(force: bool = True):
    return refresh(force=force)
