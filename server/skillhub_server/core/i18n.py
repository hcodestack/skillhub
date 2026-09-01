"""Server-side wording, in both languages the dashboard speaks.

Most of the UI translates itself in the browser, but three kinds of text are
composed here and cannot: health-section titles and hints, the exported
governance report and remediation script, and the labels of the background
jobs. Every endpoint that emits them takes `?lang=`; the SPA appends its
current language to every request, so a language switch re-fetches and the
prose follows.

One catalog, two strings per entry — a translation sits next to the text it
translates, so the pair cannot silently drift apart. `{placeholders}` are
filled by `tr(...)`.
"""
from typing import Any

DEFAULT_LANG = "en"


def normalize(lang: str | None) -> str:
    """Anything zh-ish is Chinese; everything else falls back to English."""
    return "zh" if (lang or "").lower().startswith("zh") else "en"


# key: (english, chinese)
MESSAGES: dict[str, tuple[str, str]] = {
    # ── background jobs ────────────────────────────────────────────────────
    "job.library_sync": ("Library index sync", "库索引同步"),
    "job.upstream_check": ("Upstream update check", "上游更新检查"),
    "job.vetting_scan": ("Safety review scan", "安全审查扫描"),
    "job.self_report": ("Built-in self-report", "本机自动上报"),
    "job.detail.synced": ("{n} skills indexed", "{n} 个技能入库"),
    "job.detail.upstream": (
        "{traced} traced / {checked} checked online / {cached} from cache",
        "{traced} 溯源 / {checked} 联网核对 / {cached} 用缓存",
    ),
    "job.detail.vetting": (
        "{mode}: {scanned} scanned / {flagged} flagged",
        "{mode}：{scanned} 扫描 / {flagged} 命中",
    ),
    "job.detail.vettingIdle": (
        "{mode}: nothing left to scan (all results cached)",
        "{mode}：无待扫描技能（结果均已缓存）",
    ),
    "job.mode.incremental": ("incremental", "增量"),
    "job.mode.full": ("full", "全量"),

    # ── health sections ────────────────────────────────────────────────────
    "he.jobs.title": ("Background jobs", "后台任务"),
    "he.jobs.hint": (
        "The library index sync, the upstream update check and the safety scan all "
        "run in the background. How fresh every other number on this page is depends "
        "on them — a failure turns this section red, while the rest would just go "
        "quietly stale.",
        "库索引同步、上游更新检查、安全审查扫描都在后台跑。"
        "本页其余数字的新鲜度取决于它们——失败了这里会红，其余各节则会安静地陈旧下去。",
    ),
    "he.loose.title": ("Stray copies (real directories nobody manages)",
                       "散落的实体技能（无人管理的副本）"),
    "he.loose.hint": (
        "Neither a symlink nor shipped with a repo — editing the library copy never "
        "reaches them. Bring them into the library and re-load them as symlinks.",
        "既不是软链、也不随任何仓库分发——改了真源不会同步，按管理规则应入库后改软链。",
    ),
    "he.vendored.title": ("Skills vendored inside project repos",
                          "随项目仓库分发的实体技能"),
    "he.vendored.hint": (
        "Tracked by the git repo they sit in, so they are part of that project "
        "(upstreams often publish to both .claude/skills and .agents/skills to cover "
        "several tools). They update when you pull that repo; nothing to adopt.",
        "被所在 git 仓库跟踪，属于该项目的一部分（上游常同时发布到 "
        ".claude/skills 与 .agents/skills 以兼容多个工具）。更新方式是在该仓库 git pull，无需纳管。",
    ),
    "he.broken.title": ("Broken skill symlinks (the real skill was moved or deleted)",
                        "断链的技能软链（真源已被移动或删除）"),
    "he.broken.hint": (
        "The target is gone while the directory tree around it is still there — so "
        "this is a problem with this one link, not a whole volume being offline. "
        "Fix: verify, then delete the symlink if you are done with the skill, or "
        "re-link it to the new location if you are not.",
        "目标不在了，但它所属的目录树还在——所以这是这一条的问题，不是整个卷没挂上。"
        "处理：skill doctor 复核后，不再用的删掉该软链，还要用的重新 skill load 指到新位置。",
    ),
    "he.unrooted.title": ("Undecidable symlinks (the whole target tree is unreachable)",
                          "无法判定的技能软链（真源整树不可达）"),
    "he.unrooted.hint": (
        "The target is missing together with the entire directory tree it lives in — "
        "usually a network volume that is not mounted. Mount it and wait for the next "
        "report; nothing to do about the skills themselves.",
        "目标连同它所属的目录树一起不在——多为 NAS 未挂载。挂上后重新上报即可，无需处理技能本身。",
    ),
    "he.unresolved.title": ("Invoked, but not matched to a library skill",
                            "有调用记录但未对应到库内技能"),
    "he.unresolved.hint": (
        "Usually marketplace-plugin skills or skills that were never brought into the "
        "library; adding one to the library merges its history automatically.",
        "多为 marketplace 插件技能或未入库技能；如需纳管可入库后自动归并。",
    ),
    "he.dupes.title": ("Several real copies of one skill (repo-vendored excluded)",
                       "同一技能的多份实体副本（不含仓库自带）"),
    "he.dupes.hint": (
        "Copies whose contents differ are marked — they have drifted apart and nothing "
        "says which one is current. Replacing them with symlinks to the library copy "
        "removes the problem at once.",
        "内容不一致的副本已标出——它们已各自漂移，无法判断哪份是最新。改为软链到库内真源可一次性消除。",
    ),
    "he.unindexed.title": ("Skill directories on disk that the index misses",
                           "库内存在但索引扫不到的技能目录"),
    "he.unindexed.hint": (
        "These directories hold a SKILL.md but are not in the configured index file — "
        "usually the index generator does not scan deep enough. Fix the generator, or "
        "switch to the hub's built-in scan (leave SKILLHUB_LIBRARY_INDEX unset).",
        "这些目录含 SKILL.md 却不在配置的索引文件里——通常是索引生成器的扫描深度不够。"
        "修索引工具，或改用 Hub 内置扫描（不设 SKILLHUB_LIBRARY_INDEX 即可）。",
    ),
    "he.thin.title": ("Descriptions too short to trigger reliably", "描述过短的技能（触发效果差）"),
    "he.thin.hint": (
        "A description under {n} characters cannot carry the \"when to use this\" "
        "information. The published guidance notes that models tend to under-trigger, "
        "so a description should say both what the skill does and when to reach for it. "
        "(Measured from the SKILL.md itself: an index that reads `description:` with a "
        "line regex keeps only the `|` of a YAML block scalar and would misreport.)",
        "description 不足 {n} 字符，难以承载「何时触发」的信息。"
        "官方指出模型倾向于「触发不足」，描述应同时写清做什么与何时用。"
        "（此处已按 SKILL.md 原文计算：索引里对 YAML 块标量描述只存下一个 | 字符，直接读索引会误报。）",
    ),
    "he.oversized.title": ("SKILL.md body over {n} lines", "SKILL.md 正文超过 {n} 行"),
    "he.oversized.hint": (
        "The whole body enters the context when a skill triggers; an oversized one "
        "crowds out everything else. Move detail into references/ and load it on demand.",
        "技能触发时正文整体进入上下文；过长会挤占其他内容，建议拆到 references/ 按需加载。",
    ),
    "he.safety.title": ("Safety review: high-risk signals", "安全审查：高危信号"),
    "he.safety.hint": (
        "A skill is code someone else wrote that your agent runs with your permissions. "
        "These are the high-severity hits from deterministic rules (credentials/privacy, "
        "outbound data, execution and privilege) — signals, not verdicts: curl in a "
        "web-fetching skill is the point of the skill, but it is worth your own eyes.",
        "技能是别人写的、由你的 agent 以你的权限运行的代码。"
        "这些是确定性规则命中的高危项（凭据/隐私、外发、执行提权），"
        "是信号不是判决——联网技能里出现 curl 本就正常，但值得你亲眼看一眼。",
    ),
    "he.idle.title": ("In the library, never invoked and not currently loaded",
                      "库内技能：无调用记录且当前未载入"),
    "he.idle.hint": (
        "Not a problem in itself — usage statistics only cover the tools that produce "
        "parseable logs, and only the time window collected so far. Useful as a "
        "cleanup/archive shortlist.",
        "并非问题——调用统计仅覆盖已接入的数据源与时间窗；可作为清理/归档参考。",
    ),

    # ── skill placeholders (rows the library never saw) ─────────────────────
    "skill.unmanagedDesc": (
        "Exists only in a tool entry directory; no matching skill in the library "
        "(unmanaged)",
        "仅存在于入口目录，未对应到库内技能（未纳管）",
    ),
    "skill.unresolvedDesc": (
        "Has invocation records but cannot be matched to a library skill (probably a "
        "plugin or external skill)",
        "有调用记录但无法对应到库内技能（可能是插件技能或外部技能）",
    ),

    # ── safety rules ───────────────────────────────────────────────────────
    "vet.cat.credentials": ("Credentials & privacy", "凭据与隐私"),
    "vet.cat.exfiltration": ("Outbound & downloads", "外发与下载"),
    "vet.cat.execution": ("Execution & privilege", "执行与提权"),
    "vet.rule.AGENT_MEMORY": (
        "Reads the agent's memory/identity files (MEMORY.md, CLAUDE.md, settings …) — "
        "these hold personal context and configuration",
        "读取 agent 的记忆/身份文件（MEMORY.md、CLAUDE.md、settings 等）——这些含个人上下文与配置",
    ),
    "vet.rule.CREDENTIAL_PROMPT": ("Asks the user for a password / token / key",
                                   "向用户索取密码/令牌/密钥"),
    "vet.rule.SECRET_PATHS": ("Touches credential directories (~/.ssh, ~/.aws, ~/.config)",
                              "访问 ~/.ssh、~/.aws、~/.config 等凭据目录"),
    "vet.rule.BROWSER_SESSION": (
        "Reads browser cookies / sessions (can steal a logged-in identity)",
        "读取浏览器 cookie / 会话（可窃取已登录身份）",
    ),
    "vet.rule.IP_ENDPOINT": (
        "Connects to a raw IP instead of a hostname (bypasses DNS; common in exfiltration)",
        "直连 IP 而非域名（绕过 DNS，常见于外带数据）",
    ),
    "vet.rule.REMOTE_EXEC": (
        "Downloads and executes in one step (curl | sh and friends — the content is "
        "never auditable)",
        "下载后直接执行（curl | sh 之类，内容不可审计）",
    ),
    "vet.rule.EVAL_EXEC": ("Uses eval/exec on external input", "对外部输入使用 eval/exec"),
    "vet.rule.SUDO": ("Requests sudo / privilege escalation", "请求 sudo / 提权"),
    "vet.rule.SYSTEM_WRITE": (
        "Writes to system paths outside the workspace (/etc, /usr, /var, /opt)",
        "写入工作区之外的系统路径（/etc、/usr、/var、/opt）",
    ),
    "vet.rule.DATA_POST": ("POSTs data to an external address", "向外部地址 POST 数据"),
    "vet.rule.UNPINNED_INSTALL": (
        "Installs dependencies without pinning a version (supply-chain risk)",
        "安装未固定版本的依赖（供应链风险）",
    ),
    "vet.rule.OBFUSCATED": (
        "base64-decodes then uses the result (a common way to hide real behaviour)",
        "base64 解码后使用（常用于隐藏真实行为）",
    ),

    # ── upstream update endpoint ───────────────────────────────────────────
    "src.noOrigin": ("This skill has no traceable upstream source", "该技能没有可追溯的上游来源"),
    "src.installerOwned": (
        "{kind} skills are updated by their own installer; the hub does not do it for them",
        "{kind} 类技能由其安装器更新，hub 不代劳",
    ),
    "src.outsideLibrary": ("Refused: the target path is outside the skills library",
                           "目标路径不在技能库内，已拒绝"),
    "src.notGit": ("The target is no longer a git repository", "目标已不是 git 仓库"),
    "src.statusFailed": ("git status failed: {err}", "git status 失败：{err}"),
    "src.dirtyTree": (
        "The working tree has {n} uncommitted changes; refusing to update so your "
        "edits are not overwritten",
        "工作区有 {n} 处未提交改动，拒绝更新（避免覆盖你的修改）",
    ),
    "src.reindexNote": (
        "The skill's contents changed — re-run your catalog indexer on a machine with "
        "library access, as the name/description may have changed too",
        "技能内容已变，建议在有库访问权的机器上跑 `skill index` 刷新目录（名称/描述可能已更新）",
    ),

    # ── governance report ──────────────────────────────────────────────────
    "rep.title": ("# Skillhub governance report\n", "# Skillhub 治理报告\n"),
    "rep.generated": ("> Generated {at} · hosts: {hosts}\n", "> 生成于 {at} · 主机：{hosts}\n"),
    "rep.intro": (
        "> This report can be handed straight to Claude Code / Codex: paste the file, "
        "or let it fetch the structured data itself through the skillhub MCP "
        "`remediation_plan` tool. Every cleanup happens on the machine the skills live "
        "on — the hub is read-only and cannot reach your home directory anyway.\n",
        "> 本报告可直接交给 Claude Code / Codex 执行：把文件内容贴给它，"
        "或让它通过 skillhub MCP 的 `remediation_plan` 工具自取结构化数据。"
        "所有清理都发生在技能所在的机器上——hub 是只读的，也够不着你的家目录。\n",
    ),
    "rep.summary": ("## Summary\n", "## 概览\n"),
    "rep.th.broken": ("Broken links", "断链"),
    "rep.th.loose": ("Stray copies", "散落实体"),
    "rep.th.dupes": ("Duplicate copies (drifted)", "重复副本（漂移）"),
    "rep.th.safety": ("High-risk skills", "安全高危技能"),
    "rep.badJobs": (
        "**Warning: the background jobs below are unhealthy, so these numbers may be "
        "stale:**",
        "**注意：以下后台任务不健康，本报告的数字可能陈旧：**",
    ),
    "rep.broken.h": ("## Broken links ({n}) — needs cleanup\n", "## 断链（{n}）——需要清理\n"),
    "rep.broken.intro": (
        "The symlink is still there, the real skill is not. Deleting is safe (the "
        "script re-confirms at run time that the target is still missing). Companion "
        "script: `/api/v1/report/remediation.sh`.\n",
        "软链还在、真源没了。删除是安全的（脚本会在执行时再次确认目标仍不存在）。"
        "配套脚本：`/api/v1/report/remediation.sh`。\n",
    ),
    "rep.broken.cols": ("| Tool | Entry | Dead path | Library copy |",
                        "| 工具 | 条目 | 失效路径 | 库内真源 |"),
    "rep.broken.gone": ("(no longer in the library)", "（已不在库内）"),
    "rep.loose.h": ("## Stray copies ({n}) — worth tidying\n", "## 散落实体（{n}）——建议归置\n"),
    "rep.loose.intro": (
        "Standalone copies; editing the library copy never reaches them. **Confirm by "
        "hand that a copy holds no local edits before replacing it**, which is why the "
        "commands below ship commented out in the script.\n",
        "独立拷贝，改库内真源不会同步。**替换前需人工确认副本没有本地改动**，"
        "所以下列命令在脚本里是注释状态。\n",
    ),
    "rep.loose.cols": ("| Tool | Entry | In library as | Suggestion |",
                       "| 工具 | 条目 | 库内对应 | 建议 |"),
    "rep.loose.haveLib": (
        "The library already has {id}: confirm this copy has no local edits, then "
        "delete it and replace it with a symlink to the library copy",
        "库内已有 {id}：确认这份副本没有本地改动后，删除并替换为指向库内真源的软链",
    ),
    "rep.loose.noLib": (
        "Not in the library yet: copy it in first, then delete this copy and replace "
        "it with a symlink",
        "库内没有对应技能：先复制入库，再删除此副本、换软链",
    ),
    "rep.none": ("None.\n", "无。\n"),
    "rep.dupes.h": ("## Several copies of one skill ({n}, drifted: {drifted})\n",
                    "## 同一技能的多份副本（{n}，其中漂移 {drifted}）\n"),
    "rep.dupes.drifted": ("**drifted**", "**已漂移**"),
    "rep.dupes.identical": ("identical", "内容一致"),
    "rep.dupes.line": ("- {name}: {copies} copies, {mark}", "- {name}：{copies} 份，{mark}"),
    "rep.dupes.advice": (
        " — diff them, merge back into the library copy, then switch them all to symlinks",
        "——先 diff 各份差异、合并回库内真源，再统一换软链",
    ),
    "rep.safety.h": ("## Safety review: high severity ({n} skills)\n",
                     "## 安全审查高危（{n} 个技能）\n"),
    "rep.safety.intro": (
        "Deterministic rule hits — signals, not verdicts. Open Health → Safety review "
        "in the dashboard to see the evidence for each one.\n",
        "确定性规则命中，是信号不是判决——逐个到看板「健康 → 安全审查」看具体证据。\n",
    ),
    "rep.safety.line": ("- {id} — hits: {n}", "- {id}（命中 {n} 条）"),

    # ── remediation script ─────────────────────────────────────────────────
    "sh.title": ("# Skillhub broken-link cleanup · generated {at}",
                 "# Skillhub 断链清理脚本 · 生成于 {at}"),
    "sh.hosts": ("# For hosts: {hosts} — run it on that machine",
                 "# 针对主机：{hosts} —— 在那台机器上运行"),
    "sh.none": ("(none)", "(无)"),
    "sh.explain1": (
        "# The uncommented commands do exactly one provably safe thing: remove symlinks "
        "that are STILL dangling",
        "# 未注释的命令只做一件可证明安全的事：删除「执行时仍然悬空」的软链",
    ),
    "sh.explain2": (
        "# (-L and ! -e before removing; a link repaired in the meantime is skipped).",
        "# （-L 且 ! -e 才删；期间被修复的链接会自动跳过）。",
    ),
    "sh.explain3": (
        "# Anything needing judgment (replacing stray copies) is emitted commented out — "
        "review each line and enable it yourself.",
        "# 需要人工判断的操作（散落实体替换）全部以注释给出，逐条审阅后自行放开。",
    ),
    "sh.part1": ("# ───── Part 1: clean up {n} broken links (safe, uncommented) ─────",
                 "# ───── 第 1 部分：清理 {n} 条断链（安全，未注释）─────"),
    "sh.wasPointing": ("# {agent} · {entry} · was pointing at {target}",
                       "# {agent} · {entry} · 原指向 {target}"),
    "sh.doneEcho": ('echo; echo "Broken-link cleanup done: removed=$removed skipped=$skipped"',
                    'echo; echo "断链清理完成：removed=$removed skipped=$skipped"'),
    "sh.reportEcho": (
        'echo "Run a report to zero the dashboard: python3 '
        '~/.local/lib/skillhub-reporter/skillhub_report.py 2>/dev/null || true"',
        'echo "跑一次上报让看板归零：python3 '
        '~/.local/lib/skillhub-reporter/skillhub_report.py 2>/dev/null || true"',
    ),
    "sh.part2": (
        "# ───── Part 2: these skills still exist in the library — uncomment to re-link "
        "the ones you still want ─────",
        "# ───── 第 2 部分：这些技能库内仍有真源——还要用的话，取消注释重新链接 ─────",
    ),
    "sh.part3": (
        "# ───── Part 3: stray copy → symlink (confirm the copy has NO local edits "
        "first! commented out by default) ─────",
        "# ───── 第 3 部分：散落实体 → 软链（需先确认副本无本地改动！默认注释）─────",
    ),
}


def tr(lang: str, key: str, **kw: Any) -> str:
    pair = MESSAGES.get(key)
    if pair is None:
        return key
    s = pair[1] if normalize(lang) == "zh" else pair[0]
    return s.format(**kw) if kw else s
