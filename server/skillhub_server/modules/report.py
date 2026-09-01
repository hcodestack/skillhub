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


def build_plan() -> dict:
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
            "suggestion": (
                f"库内已有 {r['skill_id']}：确认这份副本没有本地改动后，"
                f"删除并替换为指向库内真源的软链" if lib else
                "库内没有对应技能：先复制入库（自制→Self-made/，第三方→Organized/），"
                "再删除此副本、换软链"),
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
        "jobs": last_runs(),
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
def plan():
    return build_plan()


@router.get("/governance.md", response_class=PlainTextResponse)
def governance_md() -> str:
    p = build_plan()
    t = p["totals"]
    L: list[str] = []
    w = L.append
    w(f"# Skillhub 治理报告\n")
    w(f"> 生成于 {p['generated_at']} · 主机：{', '.join(p['hosts']) or '—'}\n")
    w("> 本报告可直接交给 Claude Code / Codex 执行：把文件内容贴给它，"
      "或让它通过 skillhub MCP 的 `remediation_plan` 工具自取结构化数据。"
      "所有清理都发生在技能所在的机器上——hub 是只读的，也够不着你的家目录。\n")

    w("## 概览\n")
    w(f"| 断链 | 散落实体 | 重复副本（漂移） | 安全高危技能 |")
    w(f"|---|---|---|---|")
    w(f"| {t['broken']} | {t['loose']} | {t['duplicates']}（{t['drifted']}） "
      f"| {t['safety_high']} |\n")

    bad_jobs = [j for j in p["jobs"] if j["status"] in ("failed", "stuck")]
    if bad_jobs:
        w("**注意：以下后台任务不健康，本报告的数字可能陈旧：**")
        for j in bad_jobs:
            w(f"- {j['label']}：{j['status']}（{j['error'] or j['detail']}）")
        w("")

    w(f"## 断链（{t['broken']}）——需要清理\n")
    if p["broken"]:
        w("软链还在、真源没了。删除是安全的（脚本会在执行时再次确认目标仍不存在）。"
          "配套脚本：`/api/v1/report/remediation.sh`。\n")
        w("| 工具 | 条目 | 失效路径 | 库内真源 |")
        w("|---|---|---|---|")
        for b in p["broken"]:
            w(f"| {b['agent']} | {b['entry_name']} | `{b['entry_path']}` "
              f"| {'`' + b['library_dir'] + '`' if b['library_dir'] else '（已不在库内）'} |")
        w("")
    else:
        w("无。\n")

    w(f"## 散落实体（{t['loose']}）——建议归置\n")
    if p["loose"]:
        w("独立拷贝，改库内真源不会同步。**替换前需人工确认副本没有本地改动**，"
          "所以下列命令在脚本里是注释状态。\n")
        w("| 工具 | 条目 | 库内对应 | 建议 |")
        w("|---|---|---|---|")
        for e in p["loose"]:
            w(f"| {e['agent']} | {e['entry_name']} "
              f"| {e['in_library_as'] or '—'} | {e['suggestion']} |")
        w("")
    else:
        w("无。\n")

    if p["duplicates"]:
        w(f"## 同一技能的多份副本（{t['duplicates']}，其中漂移 {t['drifted']}）\n")
        for d in p["duplicates"]:
            mark = "**已漂移**" if d["drifted"] else "内容一致"
            w(f"- {d['entry_name']}：{d['copies']} 份，{mark}"
              + ("——先 diff 各份差异、合并回库内真源，再统一换软链" if d["drifted"] else ""))
        w("")

    if p["safety_high"]:
        w(f"## 安全审查高危（{t['safety_high']} 个技能）\n")
        w("确定性规则命中，是信号不是判决——逐个到看板「健康 → 安全审查」看具体证据。\n")
        for r in p["safety_high"]:
            w(f"- {r['skill_id']}（{r['findings']} 条命中）")
        w("")

    return "\n".join(L)


@router.get("/remediation.sh", response_class=PlainTextResponse)
def remediation_sh() -> str:
    p = build_plan()
    L: list[str] = []
    w = L.append
    w("#!/usr/bin/env bash")
    w(f"# Skillhub 断链清理脚本 · 生成于 {p['generated_at']}")
    w(f"# 针对主机：{', '.join(p['hosts']) or '(无)'} —— 在那台机器上运行")
    w("#")
    w("# 未注释的命令只做一件可证明安全的事：删除「执行时仍然悬空」的软链")
    w("# （-L 且 ! -e 才删；期间被修复的链接会自动跳过）。")
    w("# 需要人工判断的操作（散落实体替换）全部以注释给出，逐条审阅后自行放开。")
    w("set -u")
    w('removed=0; skipped=0')
    w("")
    w(f"# ───── 第 1 部分：清理 {p['totals']['broken']} 条断链（安全，未注释）─────")
    for b in p["broken"]:
        q = shlex.quote(b["entry_path"])
        w(f"# {b['agent']} · {b['entry_name']} · 原指向 {b['old_target']}")
        w(f'if [ -L {q} ] && [ ! -e {q} ]; then rm {q} && echo "removed  $ {q}" '
          f'&& removed=$((removed+1)); else echo "skipped  $ {q}"; '
          f'skipped=$((skipped+1)); fi')
    w("")
    w('echo; echo "断链清理完成：removed=$removed skipped=$skipped"')
    w('echo "跑一次上报让看板归零：python3 ~/.local/lib/skillhub-reporter/'
      'skillhub_report.py 2>/dev/null || true"')
    w("")
    relink = [b for b in p["broken"] if b["relink_cmd"]]
    if relink:
        w("# ───── 第 2 部分：这些技能库内仍有真源——还要用的话，取消注释重新链接 ─────")
        for b in relink:
            w(f"# {b['relink_cmd']}")
        w("")
    replace = [e for e in p["loose"] if e["replace_cmd"]]
    if replace:
        w("# ───── 第 3 部分：散落实体 → 软链（需先确认副本无本地改动！默认注释）─────")
        for e in replace:
            w(f"# [{e['agent']}] {e['suggestion']}")
            w(f"# {e['replace_cmd']}")
        w("")
    return "\n".join(L)
