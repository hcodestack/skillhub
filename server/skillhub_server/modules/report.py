"""Report module — turn findings into things you can act on.

The dashboard found 56 broken links on Aug 31; they were all still there on
Sep 2. That gap is the product critique in one number: observation that does
not compile down to action is trivia. This module closes the loop while
keeping the hub read-only — because it has no choice: every broken link lives
in a home directory on a client machine, and a container on the NAS physically
cannot reach them. Remediation therefore ships as artifacts that execute where
the files are:

  /report/plan           structured JSON — for the MCP layer / your own agent
  /report/governance.md  human-readable snapshot — archive it, diff it, or
                         paste it to Claude Code / Codex as a work order
  /report/remediation.sh reviewable shell script — the only *uncommented*
                         commands are provably safe (remove a symlink that is
                         still dangling at execution time); everything needing
                         judgment is emitted commented-out

One builder, three renderings, so the three can never disagree.
"""
import shlex
import time

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse

from ..core.config import settings
from ..core.db import get_conn
from ..core.i18n import tr
from ..core.jobs import last_runs
from ..core.vetting import skill_dir

router = APIRouter(prefix="/report", tags=["report"])


def _display(path: str) -> str:
    """Container mount path -> the path as the user's own machine sees it."""
    root, display = settings.library_root_path, settings.library_display_path
    if root != display and path.startswith(root):
        return display + path[len(root):]
    return path


def _library_display_dir(skill_id: str) -> str:
    d = skill_dir(settings.library_root_path, skill_id)
    return _display(d) if d else ""


def build_plan(lang: str = "en") -> dict:
    conn = get_conn()
    now = time.strftime("%Y-%m-%d %H:%M:%S")

    broken = []
    for r in conn.execute(
            "SELECT host,agent,entry_name,entry_path,target_path,skill_id "
            "FROM installs WHERE active=1 AND link_type='broken' "
            "ORDER BY host,agent,entry_name").fetchall():
        lib = _library_display_dir(r["skill_id"]) if r["skill_id"] else ""
        broken.append({
            "host": r["host"], "agent": r["agent"], "entry_name": r["entry_name"],
            "entry_path": r["entry_path"], "old_target": r["target_path"],
            "library_dir": lib,
            # safe by construction: -L && ! -e re-verifies "still dangling"
            # at execution time, so a link repaired meanwhile is left alone
            "remove_cmd": (f'[ -L {shlex.quote(r["entry_path"])} ] && '
                           f'[ ! -e {shlex.quote(r["entry_path"])} ] && '
                           f'rm {shlex.quote(r["entry_path"])}'),
            "relink_cmd": (f'ln -s {shlex.quote(lib)} {shlex.quote(r["entry_path"])}'
                           if lib else ""),
        })

    loose = []
    for r in conn.execute(
            "SELECT host,agent,scope,entry_name,entry_path,skill_id "
            "FROM installs WHERE active=1 AND link_type='entity' "
            "AND vcs!='vendored' ORDER BY host,agent,entry_name").fetchall():
        if (r["agent"], r["entry_name"]) in settings.entity_whitelist():
            continue          # sanctioned entities (SKILLHUB_ENTITY_WHITELIST)
        lib = _library_display_dir(r["skill_id"]) if r["skill_id"] else ""
        loose.append({
            "host": r["host"], "agent": r["agent"], "scope": r["scope"],
            "entry_name": r["entry_name"], "entry_path": r["entry_path"],
            "in_library_as": r["skill_id"] or "", "library_dir": lib,
            # judgment required (a local edit would be lost), hence commented
            # in the script and prose here
            "suggestion": (tr(lang, "rep.loose.haveLib", id=r["skill_id"]) if lib
                           else tr(lang, "rep.loose.noLib")),
            "replace_cmd": (f'rm -rf {shlex.quote(r["entry_path"])} && '
                            f'ln -s {shlex.quote(lib)} {shlex.quote(r["entry_path"])}'
                            if lib else ""),
        })

    dupes = []
    for r in conn.execute(
            "SELECT entry_name, COUNT(*) copies, COUNT(DISTINCT content_hash) variants "
            "FROM installs WHERE active=1 AND link_type='entity' AND content_hash!='' "
            "AND vcs!='vendored' GROUP BY entry_name HAVING copies>1 "
            "ORDER BY variants DESC, copies DESC").fetchall():
        dupes.append({"entry_name": r["entry_name"], "copies": r["copies"],
                      "variants": r["variants"], "drifted": r["variants"] > 1})

    risky = []
    for r in conn.execute(
            "SELECT v.skill_id, v.top_severity, v.count FROM skill_vetting v "
            "WHERE v.top_severity='high' ORDER BY v.count DESC").fetchall():
        risky.append({"skill_id": r["skill_id"], "findings": r["count"]})

    hosts = sorted({b["host"] for b in broken} | {e["host"] for e in loose})
    return {
        "generated_at": now,
        "hosts": hosts,
        "jobs": last_runs(lang),
        "broken": broken,
        "loose": loose,
        "duplicates": dupes,
        "safety_high": risky,
        "totals": {"broken": len(broken), "loose": len(loose),
                   "duplicates": len(dupes), "drifted":
                       sum(1 for d in dupes if d["drifted"]),
                   "safety_high": len(risky)},
    }


@router.get("/plan")
def plan(lang: str = "en"):
    return build_plan(lang)


@router.get("/governance.md", response_class=PlainTextResponse)
def governance_md(lang: str = "en") -> str:
    p = build_plan(lang)
    t = p["totals"]
    L: list[str] = []
    w = L.append
    _ = lambda k, **kw: tr(lang, k, **kw)   # noqa: E731
    w(_("rep.title"))
    w(_("rep.generated", at=p["generated_at"], hosts=", ".join(p["hosts"]) or "—"))
    w(_("rep.intro"))

    w(_("rep.summary"))
    w(f"| {_('rep.th.broken')} | {_('rep.th.loose')} | {_('rep.th.dupes')} "
      f"| {_('rep.th.safety')} |")
    w("|---|---|---|---|")
    w(f"| {t['broken']} | {t['loose']} | {t['duplicates']} ({t['drifted']}) "
      f"| {t['safety_high']} |\n")

    bad_jobs = [j for j in p["jobs"] if j["status"] in ("failed", "stuck")]
    if bad_jobs:
        w(_("rep.badJobs"))
        for j in bad_jobs:
            w(f"- {j['label']}: {j['status']} ({j['error'] or j['detail']})")
        w("")

    w(_("rep.broken.h", n=t["broken"]))
    if p["broken"]:
        w(_("rep.broken.intro"))
        w(_("rep.broken.cols"))
        w("|---|---|---|---|")
        for b in p["broken"]:
            lib = f"`{b['library_dir']}`" if b["library_dir"] else _("rep.broken.gone")
            w(f"| {b['agent']} | {b['entry_name']} | `{b['entry_path']}` | {lib} |")
        w("")
    else:
        w(_("rep.none"))

    w(_("rep.loose.h", n=t["loose"]))
    if p["loose"]:
        w(_("rep.loose.intro"))
        w(_("rep.loose.cols"))
        w("|---|---|---|---|")
        for e in p["loose"]:
            w(f"| {e['agent']} | {e['entry_name']} "
              f"| {e['in_library_as'] or '—'} | {e['suggestion']} |")
        w("")
    else:
        w(_("rep.none"))

    if p["duplicates"]:
        w(_("rep.dupes.h", n=t["duplicates"], drifted=t["drifted"]))
        for d in p["duplicates"]:
            mark = _("rep.dupes.drifted") if d["drifted"] else _("rep.dupes.identical")
            w(_("rep.dupes.line", name=d["entry_name"], copies=d["copies"], mark=mark)
              + (_("rep.dupes.advice") if d["drifted"] else ""))
        w("")

    if p["safety_high"]:
        w(_("rep.safety.h", n=t["safety_high"]))
        w(_("rep.safety.intro"))
        for r in p["safety_high"]:
            w(_("rep.safety.line", id=r["skill_id"], n=r["findings"]))
        w("")

    return "\n".join(L)


@router.get("/remediation.sh", response_class=PlainTextResponse)
def remediation_sh(lang: str = "en") -> str:
    p = build_plan(lang)
    L: list[str] = []
    w = L.append
    _ = lambda k, **kw: tr(lang, k, **kw)   # noqa: E731
    w("#!/usr/bin/env bash")
    w(_("sh.title", at=p["generated_at"]))
    w(_("sh.hosts", hosts=", ".join(p["hosts"]) or _("sh.none")))
    w("#")
    w(_("sh.explain1"))
    w(_("sh.explain2"))
    w(_("sh.explain3"))
    w("set -u")
    w('removed=0; skipped=0')
    w("")
    w(_("sh.part1", n=p["totals"]["broken"]))
    for b in p["broken"]:
        q = shlex.quote(b["entry_path"])
        w(_("sh.wasPointing", agent=b["agent"], entry=b["entry_name"],
            target=b["old_target"]))
        w(f'if [ -L {q} ] && [ ! -e {q} ]; then rm {q} && echo "removed  $ {q}" '
          f'&& removed=$((removed+1)); else echo "skipped  $ {q}"; '
          f'skipped=$((skipped+1)); fi')
    w("")
    w(_("sh.doneEcho"))
    w(_("sh.reportEcho"))
    w("")
    relink = [b for b in p["broken"] if b["relink_cmd"]]
    if relink:
        w(_("sh.part2"))
        for b in relink:
            w(f"# {b['relink_cmd']}")
        w("")
    replace = [e for e in p["loose"] if e["replace_cmd"]]
    if replace:
        w(_("sh.part3"))
        for e in replace:
            w(f"# [{e['agent']}] {e['suggestion']}")
            w(f"# {e['replace_cmd']}")
        w("")
    return "\n".join(L)
