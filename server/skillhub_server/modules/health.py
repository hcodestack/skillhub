"""Health module — governance findings derived from reported state.
Read-only observations; fixing stays with the `skill` CLI per policy."""
from fastapi import APIRouter

import os

from ..core.config import settings
from ..core.quality import (LONG_BODY_LINES, SHORT_DESC_CHARS, body_lines)
from ..core.db import get_conn
from ..core.jobs import last_runs

router = APIRouter(prefix="/health", tags=["health"])

# Sanctioned entries that are legitimately entities in entry dirs — configure
# via SKILLHUB_ENTITY_WHITELIST="agent:entry,agent:entry".
def WHITELIST():
    return settings.entity_whitelist()


@router.get("/findings")
def findings():
    conn = get_conn()
    sections = []

    # First, because everything below it is only as fresh as these three runs.
    # A failed sync or scan used to be visible only in `docker logs`, so the
    # dashboard would keep showing yesterday's numbers with nothing to say so.
    jobs = last_runs()
    bad = [j for j in jobs if j["status"] in ("failed", "stuck")]
    sections.append({
        "key": "background_jobs",
        "severity": "error" if bad else "info",
        "title": "后台任务",
        "hint": ("库索引同步、上游更新检查、安全审查扫描都在后台跑。"
                 "本页其余数字的新鲜度取决于它们——失败了这里会红，"
                 "其余各节则会安静地陈旧下去。"),
        # count is the item count here as in every other section; whether to
        # worry is what the severity chip says
        "count": len(jobs), "items": jobs,
    })

    rows = [dict(r) for r in conn.execute(
        "SELECT host,agent,scope,project_path,entry_name,entry_path,link_type,vcs "
        "FROM installs WHERE active=1 AND link_type='entity'").fetchall()]
    wl = WHITELIST()
    entity = [r for r in rows if (r["agent"], r["entry_name"]) not in wl]

    # A skill committed inside a cloned repo is not a stray copy — it shipped
    # with that project and is updated by pulling it. Reporting the two together
    # buries the ones that actually need attention.
    loose = [r for r in entity if r["vcs"] != "vendored"]
    vendored = [r for r in entity if r["vcs"] == "vendored"]

    sections.append({
        "key": "loose_entities", "severity": "warn",
        "title": "散落的实体技能（无人管理的副本）",
        "hint": ("既不是软链、也不随任何仓库分发——改了真源不会同步，"
                 "按管理规则应入库后改软链。"),
        "count": len(loose), "items": loose,
    })
    sections.append({
        "key": "vendored_entities", "severity": "info",
        "title": "随项目仓库分发的实体技能",
        "hint": ("被所在 git 仓库跟踪，属于该项目的一部分（上游常同时发布到 "
                 ".claude/skills 与 .agents/skills 以兼容多个工具）。"
                 "更新方式是在该仓库 git pull，无需纳管。"),
        "count": len(vendored), "items": vendored,
    })

    broken = [dict(r) for r in conn.execute(
        "SELECT host,agent,scope,project_path,entry_name,entry_path,target_path "
        "FROM installs WHERE active=1 AND link_type='broken'").fetchall()]
    sections.append({
        "key": "broken_links", "severity": "error",
        "title": "断链的技能软链（真源已被移动或删除）",
        "hint": ("目标不在了，但它所属的目录树还在——所以这是这一条的问题，"
                 "不是整个卷没挂上。处理：skill doctor 复核后，"
                 "不再用的删掉该软链，还要用的重新 skill load 指到新位置。"),
        "count": len(broken), "items": broken,
    })

    # Separated from the above on purpose: when the NAS is unmounted every
    # symlink into the library fails at once. Counting those as broken would
    # bury the handful that are genuinely stale under a flood, and the fix
    # ("mount the NAS") has nothing to do with the skills.
    unrooted = [dict(r) for r in conn.execute(
        "SELECT host,agent,scope,project_path,entry_name,entry_path,target_path "
        "FROM installs WHERE active=1 AND link_type='unrooted'").fetchall()]
    sections.append({
        "key": "unrooted_links", "severity": "info",
        "title": "无法判定的技能软链（真源整树不可达）",
        "hint": ("目标连同它所属的目录树一起不在——多为 NAS 未挂载。"
                 "挂上后重新上报即可，无需处理技能本身。"),
        "count": len(unrooted), "items": unrooted,
    })

    unresolved = [dict(r) for r in conn.execute(
        "SELECT skill_key, COUNT(*) n, MAX(ts) last, GROUP_CONCAT(DISTINCT agent) agents "
        "FROM usage_events WHERE skill_id IS NULL "
        "GROUP BY skill_key ORDER BY n DESC").fetchall()]
    sections.append({
        "key": "unresolved_usage", "severity": "info",
        "title": "有调用记录但未对应到库内技能",
        "hint": "多为 marketplace 插件技能或未入库技能；如需纳管可入库后自动归并。",
        "count": len(unresolved), "items": unresolved,
    })

    # Same skill copied into several tools: fine when identical, a real problem
    # when the copies have drifted apart — nobody knows which one is current.
    dupes = []
    for r in conn.execute(
            "SELECT entry_name, COUNT(*) copies, "
            "COUNT(DISTINCT content_hash) variants, "
            "GROUP_CONCAT(DISTINCT agent) agents "
            "FROM installs WHERE active=1 AND link_type='entity' AND content_hash!='' "
            "AND vcs!='vendored' "
            "GROUP BY entry_name HAVING copies > 1 "
            "ORDER BY variants DESC, copies DESC").fetchall():
        dupes.append({**dict(r), "drifted": r["variants"] > 1})
    drifted = [d for d in dupes if d["drifted"]]
    sections.append({
        "key": "duplicate_copies", "severity": "warn" if drifted else "info",
        "title": "同一技能的多份实体副本（不含仓库自带）",
        "hint": ("内容不一致的副本已标出——它们已各自漂移，无法判断哪份是最新。"
                 "改为软链到库内真源可一次性消除。"),
        "count": len(dupes), "items": dupes,
    })

    # Skills on disk that the external index missed (only meaningful when an
    # index file is configured — the built-in scan has no such blind spot).
    if settings.library_index:
        unindexed = []
        known = {r["id"] for r in conn.execute("SELECT id FROM skills").fetchall()}
        for base in settings.library_bases():
            base_name = os.path.basename(base.rstrip(os.sep))
            for dirpath, dirnames, filenames in os.walk(base):
                dirnames[:] = [d for d in dirnames
                               if d not in (".git", "node_modules", ".venv")]
                if not any(f.lower() == "skill.md" for f in filenames):
                    continue
                rel = os.path.relpath(dirpath, base)
                if rel == ".":
                    continue
                rid = rel.replace(os.sep, "/")
                if rid not in known and "/".join(rid.split("/")[:2]) not in known:
                    unindexed.append({"path": f"{base_name}/{rel}"})
        sections.append({
            "key": "unindexed_skills", "severity": "warn",
            "title": "库内存在但索引文件没收录的技能目录",
            "hint": ("这些目录含 SKILL.md 却不在配置的索引文件里——通常是索引生成器"
                     "的扫描深度不够。修索引工具，或改用 Hub 内置扫描"
                     "（不设 SKILLHUB_LIBRARY_INDEX 即可）。"),
            "count": len(unindexed), "items": unindexed,
        })

    # Description quality: it is the trigger mechanism and sits in context every
    # turn, so a thin one means the skill silently never fires.
    thin = [dict(r) for r in conn.execute(
        "SELECT id, name, LENGTH(description) chars FROM skills "
        "WHERE in_library=1 AND LENGTH(description) < ? ORDER BY chars",
        (SHORT_DESC_CHARS,)).fetchall()]
    sections.append({
        "key": "thin_descriptions", "severity": "warn",
        "title": "描述过短的技能（触发效果差）",
        "hint": (f"description 不足 {SHORT_DESC_CHARS} 字符，难以承载「何时触发」的信息。"
                 "官方指出模型倾向于「触发不足」，描述应同时写清做什么与何时用。"
                 "（此处已按 SKILL.md 原文计算：skills-index.json 对 YAML 块标量"
                 "描述只存下一个 | 字符，直接读索引会误报。）"),
        "count": len(thin), "items": thin,
    })

    oversized = [{"id": r["id"], "lines": r["body_lines"]} for r in conn.execute(
        "SELECT id, body_lines FROM skills WHERE in_library=1 AND body_lines > ? "
        "ORDER BY body_lines DESC", (LONG_BODY_LINES,)).fetchall()]
    sections.append({
        "key": "oversized_bodies", "severity": "info",
        "title": f"SKILL.md 正文超过 {LONG_BODY_LINES} 行",
        "hint": "技能触发时正文整体进入上下文；过长会挤占其他内容，建议拆到 references/ 按需加载。",
        "count": len(oversized), "items": oversized,
    })

    from .vetting import findings_map
    vets = findings_map()
    risky = []
    for sid, v in vets.items():
        for f in v["findings"]:
            if f["severity"] == "high":
                risky.append({"id": sid, "rule": f["rule"], "category": f["category"],
                              "description": f["description"],
                              "where": f'{f["file"]}:{f["line"]}',
                              "excerpt": f["excerpt"]})
    risky.sort(key=lambda x: x["id"])
    sections.append({
        "key": "safety_high", "severity": "warn",
        "title": "安全审查：高危信号",
        "hint": ("技能是别人写的、由你的 agent 以你的权限运行的代码。"
                 "这些是确定性规则命中的高危项（凭据/隐私、外发、执行提权），"
                 "是信号不是判决——联网技能里出现 curl 本就正常，但值得你亲眼看一眼。"),
        "count": len(risky), "items": risky,
    })

    never = [dict(r) for r in conn.execute(
        "SELECT s.id, s.name, s.source, s.category FROM skills s "
        "WHERE s.in_library=1 "
        "AND NOT EXISTS(SELECT 1 FROM usage_events u WHERE u.skill_id=s.id) "
        "AND NOT EXISTS(SELECT 1 FROM installs i WHERE i.skill_id=s.id AND i.active=1) "
        "ORDER BY s.id").fetchall()]
    sections.append({
        "key": "idle_skills", "severity": "info",
        "title": "库内技能：无调用记录且当前未载入",
        "hint": "并非问题——调用统计仅覆盖已接入的数据源与时间窗；可作为清理/归档参考。",
        "count": len(never), "items": never,
    })

    return {"sections": sections}
