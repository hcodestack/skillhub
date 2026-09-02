import { useSyncExternalStore } from 'react';

/* Dashboard localisation.
 *
 * English is the default so the project reads to anyone who opens it; the
 * previous UI was Chinese-only. One catalog holds both languages side by side
 * — a message is a single entry with two strings, so a translation cannot
 * silently drift away from the text it translates, which is what happens when
 * the two live in separate files.
 *
 * Resolution order: `?lang=` in the URL (a shareable one-shot override, then
 * remembered) → localStorage → English. Deliberately NOT navigator.language:
 * the default has to be predictable for a dashboard whose screenshots and docs
 * are English.
 *
 * Server-rendered prose (health section titles, the governance report) is
 * localised on the server instead — `api()` appends the current language to
 * every request. */

export type Lang = 'en' | 'zh';

export const LANGS: { id: Lang; label: string }[] = [
  { id: 'en', label: 'EN' },
  { id: 'zh', label: '中文' },
];

const STORAGE_KEY = 'skillhub-lang';

const M = {
  // ── shell ──────────────────────────────────────────────────────────────
  'app.title': ['Skillhub — local skill overview', 'Skillhub — 本地技能总揽'],
  'app.subtitle': [
    'Every skill you own — inventory · load topology · usage',
    '本地技能总揽 — 库存 · 载入拓扑 · 调用记录',
  ],
  'app.modules': ['Modules', '模块'],
  'app.language': ['Language', '语言'],
  'app.theme': ['Appearance', '外观'],
  'app.theme.system': ['System', '跟随系统'],
  'app.theme.light': ['Light', '浅色'],
  'app.theme.dark': ['Dark', '深色'],
  'app.badge.health': [
    '{n} findings need attention', '{n} 项发现需要关注'],
  'app.badge.updates': ['{n} skills have an upstream update', '{n} 个技能有上游更新'],

  'nav.overview': ['Overview', '总览'],
  'nav.topology': ['Topology', '拓扑'],
  'nav.updates': ['Updates', '更新'],
  'nav.health': ['Health', '健康'],
  'nav.hosts': ['Hosts', '主机'],

  // ── shared vocabulary ──────────────────────────────────────────────────
  'common.loading': ['Loading', '加载中'],
  'common.copy': ['Copy', '复制'],
  'common.copied': ['Copied', '已复制'],
  'common.global': ['global', '全局'],
  'common.project': ['project', '项目'],
  'common.none': ['None', '无'],
  'common.uncategorized': ['Uncategorized', '未分类'],
  'common.count': ['{n}', '{n}'],

  'rel.minutes': ['{n} min ago', '{n} 分钟前'],
  'rel.hours': ['{n} h ago', '{n} 小时前'],
  'rel.days': ['{n} d ago', '{n} 天前'],

  'path.library': ['library', '库'],

  // ── source / update / severity vocabulary ──────────────────────────────
  'source.organized': ['Third-party', '第三方库'],
  'source.self-made': ['Own', '自制库'],
  'source.installer': ['Installer', '安装器'],
  'source.unmanaged': ['Unmanaged', '未纳管'],
  'source.unresolved': ['External / plugin', '外部/插件'],

  'update.behind': ['Update available', '有更新'],
  'update.current': ['Up to date', '最新'],
  'update.moved': ['New upstream commits', '上游有新提交'],
  'update.tracked': ['Upstream recorded', '已记录上游'],
  'update.installer': ['Installer-managed', '安装器管理'],
  'update.error': ['Check failed', '检查失败'],
  'update.unknown': ['Unknown', '未知'],

  'sev.high': ['High', '高危'],
  'sev.medium': ['Medium', '中'],
  'sev.low': ['Low', '低'],

  'agent.shared': ['shared ', '共享 '],

  // ── domain tags (stable keys stored by the server, labelled here) ───────
  'cat.meta': ['Meta / skill building', 'Meta/技能构建'],
  'cat.office': ['Office & collaboration', '办公协同'],
  'cat.audio': ['Audio & voice', '音频/语音'],
  'cat.video': ['Video & motion', '视频/动效'],
  'cat.3d': ['3D & characters', '3D/角色'],
  'cat.image': ['Image', '图像'],
  'cat.design': ['Design / UI', '设计/UI'],
  'cat.docs': ['Document output', '文档产出'],
  'cat.cn-social': ['Chinese social media', '中文社媒'],
  'cat.seo': ['SEO & marketing', 'SEO/营销'],
  'cat.writing': ['Writing', '写作'],
  'cat.web': ['Web access & scraping', '联网/抓取'],
  'cat.data': ['Data & analysis', '数据/分析'],
  'cat.dev': ['Dev & cloud', '开发/云'],
  'cat.standalone': ['Standalone', '独立'],
  'cat.unmanaged': ['Unmanaged', '未纳管'],
  'cat.external': ['External / plugin', '外部/插件'],

  // ── link states (the canonical explainer) ──────────────────────────────
  'verdict.ok': ['Nothing to do', '无需处理'],
  'verdict.attention': ['Worth tidying', '建议归置'],
  'verdict.fix': ['Needs cleanup', '需要清理'],
  'verdict.env': ['Just mount it', '挂载即可'],

  'link.symlink': ['Symlink', '软链'],
  'link.vendored': ['Repo-vendored', '仓库自带'],
  'link.entity': ['Stray copy', '散落实体'],
  'link.broken': ['Broken link', '断链'],
  'link.unrooted': ['Undecidable', '无法判定'],

  'link.symlink.what': [
    'A symbolic link created by your loader, pointing at the real skill in the '
    + 'library. The skill itself exists once, in the library; this is only a door to it.',
    '由 skill load 建立的符号链接，指向技能库里的真源。技能本体只有库里一份，这里只是个入口。',
  ],
  'link.symlink.action': [
    'This is the target state: edit the one copy in the library and every tool that '
    + 'loaded it picks up the change.',
    '这就是目标状态：改库内真源，所有装了它的工具同时生效。',
  ],
  'link.vendored.what': [
    'A real directory, but tracked by the git repo it sits in — you did not install '
    + 'it, the project author committed the skill and it arrives with a clone '
    + '(upstreams often publish to both .claude/skills and .agents/skills to cover '
    + 'several tools).',
    '实体目录，但被所在项目的 git 仓库跟踪——不是你装的，是项目作者把技能'
    + '提交进了仓库，克隆时就带着（上游常同时放 .claude/skills 与 .agents/skills 两份以兼容多个工具）。',
  ],
  'link.vendored.action': [
    'Nothing to clean up and nothing to adopt: it belongs to that project and updates '
    + 'when you pull the repo.',
    '不用清理、也不必收进库：它属于那个项目，在该仓库 git pull 就会跟着更新。',
  ],
  'link.entity.what': [
    'A standalone copy of the directory: neither a symlink nor shipped with any repo. '
    + 'Usually a manual copy, an installer writing straight into a tool directory, or '
    + 'a leftover from before the library existed. The risk: editing the library copy '
    + 'does not reach it, and several same-named copies drift apart independently '
    + '(the dashboard watches this by content hash).',
    '独立的目录拷贝：既不是软链、也不随任何仓库分发。通常来自手动复制安装、'
    + '某些安装器直接写入、或纳管之前的历史遗留。风险在于：改了库内真源它不会跟着变，'
    + '同名的几份副本各改各的就漂移了（看板按内容哈希在盯）。',
  ],
  'link.entity.action': [
    'Worth tidying — if the library already has it: delete this copy and re-load it as '
    + 'a symlink. If not: copy it into the library first, then replace it with a symlink.',
    '建议归置——库里已有同源的：删掉这份副本，需要就 skill load 换成软链；'
    + '库里还没有的：先复制入库，再换软链。',
  ],
  'link.broken.what': [
    'The symlink is still there, its target is gone — the real skill was moved, renamed '
    + 'or retired and the stale links in the tool directories were never cleaned up. The '
    + 'check already confirmed the directory tree around the target is reachable, so this '
    + 'is not an unmounted volume: this one link really is dead, and the skill does not '
    + 'work in that tool.',
    '软链还在、指向的目标没了——真源被移动、重命名或退役后，各工具目录里的'
    + '旧链接没跟着清理。判定时已确认目标所在的目录树还在——已排除「NAS 没挂载」'
    + '的情况，是这一条真的失效了。这个工具里该技能实际已经用不了。',
  ],
  'link.broken.action': [
    'Needs cleanup: verify first, then delete the symlink if you no longer want the '
    + 'skill, or re-link it to the new location if you do.',
    '需要清理：先 skill doctor 复核；不再用的直接删掉该软链，还要用的重新 skill load 指到新位置。',
  ],
  'link.unrooted.what': [
    'The link target is unreachable together with the whole directory tree it lives in '
    + '— almost always a network volume (NAS) that is not mounted, rather than anything '
    + 'wrong with the skill.',
    '软链目标连同它所在的整棵目录树都不可达——几乎总是网络盘（NAS）没挂载，而不是技能出了问题。',
  ],
  'link.unrooted.action': [
    'Mount it and wait for the next report. Nothing to change about the skill itself.',
    '挂载后等下一次上报即可，技能本身什么都不用动。',
  ],
  'link.action.prefix': ['What to do: ', '怎么办：'],
  'link.explain.open': ['What are these?', '这些是什么？'],
  'link.explain.close': ['Hide explanation', '收起说明'],

  // short notes used in chips / legend hovers
  'link.note.symlink': [
    'Points at the library copy — update once, effective everywhere',
    '指向库内真源，更新一次处处生效',
  ],
  'link.note.vendored': [
    'Ships with its git repo (upstreams often publish to both .claude/skills and '
    + '.agents/skills for multi-tool support) — updates via git pull in that repo, '
    + 'nothing to adopt',
    '随所在 git 仓库分发（上游常同时发布到 .claude/skills 与 .agents/skills 以兼容多工具）'
    + '——更新靠在该仓库 git pull，无需纳管',
  ],
  'link.note.entity': [
    'A standalone copy, neither linked nor repo-tracked: library edits never reach it '
    + 'and copies drift apart over time',
    '既不是链接、也不随任何仓库分发的独立拷贝，改真源不会同步，久了会各自漂移',
  ],
  'link.note.broken': [
    'The link target no longer exists (the real skill was moved or deleted) — in this '
    + 'tool the skill simply does not work',
    '软链指向的目标已不存在（真源被移动或删除后旧链接没清理）——该工具里这个技能实际用不了',
  ],
  'link.note.symlinkFull': [
    'Points at the library copy, update once and it lands everywhere — the target '
    + 'state, nothing to do',
    '指向库内真源，更新一次处处生效——目标状态，无需处理',
  ],
  'link.note.vendoredFull': [
    'Vendored in the project repo (the author committed it, a clone brings it) — '
    + 'updates with that repo, nothing to clean up or adopt',
    '项目仓库自带（作者提交进去的，克隆时就有）——随该仓库 git pull 更新，无需清理或纳管',
  ],
  'link.note.entityFull': [
    'A standalone copy: library edits never reach it and several copies drift — bring '
    + 'it into the library and re-load it as a symlink',
    '独立拷贝：改库内真源不会同步到它，多份副本会漂移——建议入库后换成 skill load 软链',
  ],
  'link.note.brokenFull': [
    'The link target is gone (the real skill was moved or deleted) — delete the link if '
    + 'you are done with it, re-link it if not',
    '软链目标已不存在（真源被移动或删除）——不再用就删掉，还要用就重新 skill load',
  ],

  // ── overview ───────────────────────────────────────────────────────────
  'ov.tile.library': ['Skills in library', '库内技能'],
  'ov.tile.loaded': ['Loaded (deduped)', '已载入（去重）'],
  'ov.tile.events': ['Invocations', '累计调用'],
  'ov.tile.events7': ['Invocations, 7d', '近 7 天调用'],
  'ov.tile.loose': ['Stray copies', '散落实体'],
  'ov.tile.loose.title': [
    'Unmanaged real copies — click for the list',
    '无人管理的实体副本 — 点击查看明细',
  ],
  'ov.tile.broken': ['Broken links', '断链'],
  'ov.tile.broken.title': [
    'Symlinks whose target was moved or deleted — click for the list',
    '真源已被移动或删除的软链 — 点击查看明细',
  ],
  'ov.tile.tools': ['Tools', '工具'],
  'ov.tile.hosts': ['Hosts', '主机'],
  'ov.tile.tokens': ['Resident metadata tokens', '常驻元数据 tokens'],
  'ov.tile.tokens.title': [
    'Every loaded skill keeps its name+description in context on every turn; this '
    + 'estimates how much that costs',
    '已载入技能的 name+description 每轮对话都常驻上下文；这是其体积估算',
  ],

  'ov.search': ['Search skills', '搜索技能'],
  'ov.search.placeholder': [
    'Search id / name / description / tag',
    '搜索 id / 名称 / 描述 / 标签',
  ],
  'ov.filter.source': ['Source', '来源'],
  'ov.filter.source.all': ['Source: all', '来源：全部'],
  'ov.filter.tool': ['Tool', '工具'],
  'ov.filter.tool.all': ['Tool: all', '工具：全部'],
  'ov.filter.category': ['Category', '分类'],
  'ov.filter.category.all': ['Category: all', '分类：全部'],
  'ov.filter.state': ['State', '状态'],
  'ov.filter.state.all': ['State: all', '状态：全部'],
  'ov.filter.state.loaded': ['Loaded', '已载入'],
  'ov.filter.state.used': ['Has usage', '有调用'],
  'ov.filter.state.unused': ['Never used', '未使用'],
  'ov.filter.state.behind': ['Update available', '有上游更新'],
  'ov.filter.state.risky': ['Safety: high', '安全高危'],
  'ov.results': ['{n} shown', '{n} 项'],
  'ov.filter.tags': ['Tags', '标签'],
  'ov.filter.tags.n': ['Tags: {n}', '标签：{n}'],
  'ov.tags.title': ['Domain tags', '领域标签'],
  'ov.tags.matchAny': ['match any', '任一匹配'],
  'ov.tags.search': ['Search tags', '搜索标签'],
  'ov.tags.untagged': ['Untagged', '未打标签'],
  'ov.tags.clear': ['Clear', '清除'],
  'ov.view': ['View', '视图'],
  'ov.view.list': ['List', '列表'],
  'ov.view.cards': ['Cards', '卡片'],

  'ov.col.skill': ['Skill', '技能'],
  'ov.col.source': ['Source', '来源'],
  'ov.col.agents': ['Agents · usage split', 'Agents · 调用分布'],
  'ov.col.installs': ['Loads', '载入'],
  'ov.col.usage': ['Usage', '调用'],
  'ov.col.d7': ['7d', '7 天'],
  'ov.col.last': ['Last used', '最近调用'],
  'ov.table': ['Skill list', '技能列表'],
  'ov.empty': ['No matching skills', '没有匹配的技能'],
  'ov.chip.unmanaged': ['Unmanaged', '未纳管'],
  'ov.chip.external': ['External', '外部'],
  'ov.chip.high': ['High risk', '高危'],
  'ov.chip.update': ['Update', '有更新'],
  'ov.installs.split': ['({g} global / {p} project)', '（{g} 全局 / {p} 项目）'],

  // ── skill drawer ───────────────────────────────────────────────────────
  'dr.noDescription': ['(no description)', '（无描述）'],
  'dr.source': ['Real source', '真源'],
  'dr.source.unmanagedHint': ['Unmanaged — no library copy', '未纳管，无库内真源'],
  'dr.source.path': ['Library path', '库内路径'],
  'dr.source.upstream': ['Upstream', '上游'],
  'dr.source.size': ['Size', '体量'],
  'dr.source.sizeValue': [
    'SKILL.md {lines} lines · description {chars} chars',
    'SKILL.md {lines} 行 · 描述 {chars} 字符',
  ],
  'dr.source.tooLong': ['over the recommended 500 lines', '超过官方建议的 500 行'],
  'dr.source.entryOnly': [
    'This skill exists only in a tool entry directory; there is no matching copy in the library.',
    '这个技能只存在于工具入口目录，库内没有对应真源。',
  ],
  'dr.safety': ['Safety review', '安全审查'],
  'dr.safety.hasHigh': ['contains high-risk signals', '含高危信号'],
  'dr.safety.note': [
    'Deterministic rule hits — signals, not verdicts. curl in a web-fetching skill is '
    + 'the point of the skill; these lines are just worth a look with your own eyes.',
    '确定性规则命中，是信号不是判决——联网技能里出现 curl 本就正常，但值得你亲眼看一眼这几行。',
  ],
  'dr.safety.chip': ['Safety: high', '安全高危'],
  'dr.installs': ['Load sites', '载入位置'],
  'dr.installs.none': ['Not loaded into any entry directory.', '当前未载入到任何入口。'],
  'dr.installs.count': ['{n} here', '{n} 处'],
  'dr.installs.shared': ['This directory also serves: {list}', '此目录同时服务：{list}'],
  'dr.events': ['Invocations', '调用记录'],
  'dr.events.last': ['last {when}', '最近 {when}'],
  'dr.events.never': ['no invocations yet', '暂无调用'],
  'dr.events.none': ['No invocations recorded.', '暂无调用记录。'],
  'dr.events.more': ['Load more ({shown}/{total})', '加载更多（{shown}/{total}）'],
  'dr.eval.copy': ['Copy evaluation prompt', '复制评估提示词'],
  'dr.eval.hint': [
    'Paste into Claude Code and evaluate with skill-creator (no model runs in this dashboard)',
    '粘进 Claude Code 用 skill-creator 评估（本看板不内置模型）',
  ],
  'dr.eval.prompt': [
    'Use the skill-creator skill to evaluate this skill and suggest improvements:\n'
    + '- skill id: {id}\n{path}'
    + 'Focus on: whether the description triggers reliably (does it say WHEN to use it), '
    + 'whether the SKILL.md body length and structure are reasonable, and whether content '
    + 'should move into references/.\n'
    + 'If it is worth it, design 2-3 test cases and run one comparison with vs. without the skill.',
    '使用 skill-creator 技能，评估这个技能并给出改进建议：\n'
    + '- 技能 id：{id}\n{path}'
    + '请重点看：description 能否可靠触发（是否写清了「何时用」）、'
    + 'SKILL.md 正文长度与结构是否合理、是否该把内容下沉到 references/。\n'
    + '如果值得，再设计 2-3 个测试用例并跑一轮带技能 vs 基线的对比。',
  ],
  'dr.eval.promptPath': ['- path: {path}\n', '- 路径：{path}\n'],

  // ── health ─────────────────────────────────────────────────────────────
  'he.sev.error': ['Error', '异常'],
  'he.sev.warn': ['Attention', '关注'],
  'he.sev.info': ['Note', '提示'],
  'he.job.ok': ['OK', '正常'],
  'he.job.failed': ['Failed', '失败'],
  'he.job.stuck': ['Stuck', '卡住'],
  'he.job.running': ['Running', '运行中'],
  'he.job.never': ['Never ran', '未运行'],
  'he.job.runningFor': ['running for', '已运行'],
  'he.job.finishedAt': ['finished', '结束于'],
  'he.job.took': [', took {d}', '，耗时 {d}'],
  'he.dur.subSecond': ['<1s', '<1 秒'],
  'he.dur.seconds': ['{n}s', '{n} 秒'],
  'he.dur.minutes': ['{m}m {s}s', '{m} 分 {s} 秒'],
  'he.intro': [
    'The words symlink / repo-vendored / stray copy / broken link recur below —',
    '下面各节反复出现「软链 / 仓库自带 / 散落实体 / 断链」——',
  ],
  'he.export.report': ['Export governance report', '导出治理报告'],
  'he.export.reportFile': ['skillhub-governance-report.md', 'skillhub-治理报告.md'],
  'he.export.script': ['Download cleanup script', '下载清理脚本'],
  'he.export.scriptFile': ['skillhub-remediation.sh', 'skillhub-清理脚本.sh'],
  'he.export.scriptTitle': [
    'Only "delete links that are still dangling" is uncommented; everything else is '
    + 'emitted commented out for you to review and enable',
    '只有「删除仍悬空的软链」是未注释的；其余操作以注释给出，审阅后自行放开',
  ],
  'he.item.chars': ['{n} chars', '{n} 字符'],
  'he.item.lines': ['{n} lines', '{n} 行'],
  'he.item.copies': ['{n} copies', '{n} 份副本'],
  'he.item.drifted': ['content differs ({n} variants)', '内容不一致（{n} 种）'],
  'he.item.identical': ['identical content', '内容一致'],
  'he.item.times': ['{n}×', '{n} 次'],
  'he.item.last': ['last {when}', '最近 {when}'],
  'he.item.more': ['+{n} more', '+{n} 更多'],

  // ── updates ────────────────────────────────────────────────────────────
  'up.traceable': [
    'Upstream traceable for {n} of {total} skills in the library '
    + '({untraced} have no recorded source and cannot be checked)',
    '可追溯上游 {n} / 库内 {total}（{untraced} 个来源未记录，无法检查更新）',
  ],
  'up.recheck': ['Re-check upstreams', '重新检查上游'],
  'up.rechecking': ['Checking…', '检查中…'],
  'up.checkFailed': [
    'Check failed ({err}); the list below is still the previous result',
    '检查失败（{err}）；下方仍为上次结果',
  ],
  'up.behind.title': ['Skills with an upstream update', '上游已更新的技能'],
  'up.behind.desc': [
    'The library copy is behind its upstream repo. "Update" runs {cmd}: it touches only '
    + 'the library copy, never a symlink entry, and refuses if the working tree has '
    + 'uncommitted changes, so your edits are never overwritten.',
    '库内版本落后于上游仓库。「一键更新」执行 {cmd}：'
    + '只改库内真源、不动任何软链入口；工作区若有未提交改动会被拒绝，不覆盖你的修改。',
  ],
  'up.behind.none': ['Everything is up to date.', '全部为最新。'],
  'up.checkedAt': ['checked {when}', '检查于 {when}'],
  'up.button': ['Update', '一键更新'],
  'up.button.busy': ['Updating…', '更新中…'],
  'up.done': ['Updated {from} → {to}{note}', '已更新 {from} → {to}{note}'],
  'up.alreadyCurrent': ['Already up to date', '已是最新'],
  'up.failed': ['Not updated: {err}', '未更新：{err}'],
  'up.requestFailed': ['Request failed: {err}', '请求失败：{err}'],
  'up.copyCmd': ['Copy command', '复制命令'],
  'up.moved.title': ['Upstream has moved since it was recorded', '上游仓库自记录以来已更新'],
  'up.moved.desc': [
    'These skills were copied into the library from an upstream repo and carry no local '
    + 'revision of their own, so all that can be said is that the upstream has new '
    + 'commits — whether to re-sync is your call.',
    '这些技能是从上游仓库复制进库的，本地没有自己的版本号，只能判断上游是否有了新提交'
    + ' —— 是否需要同步要你自行判断。',
  ],
  'up.rest.title': ['Other traceable skills', '其余可追溯技能'],
  'up.rest.desc': [
    'Installer-managed skills are updated by their own installer (e.g. its `update` command).',
    '安装器管理的技能由其自身更新器负责（例如它自己的 update 命令）。',
  ],
  'up.inferred': ['inferred source', '来源为推断'],

  // ── hosts ──────────────────────────────────────────────────────────────
  'ho.none': ['No host has reported yet.', '还没有主机上报过数据。'],
  'ho.lastReport': ['last report {when}', '最近上报 {when}'],
  'ho.entries': [
    '{n} entries ({g} global / {p} project)',
    '{n} 入口（全局 {g} / 项目 {p}）',
  ],
  'ho.total': ['Invocations', '累计调用'],
  'ho.tile.detected': ['Tools detected', '检测到的工具'],
  'ho.tile.loaded': ['With skills loaded', '载入了技能的'],
  'ho.tile.entries': ['Entries', '入口条目'],
  'ho.tile.undetected': ['Not on this host', '本机未安装'],
  'ho.tile.undetected.title': [
    'Tools the reporter knows how to scan but found no home directory for',
    '上报器认识、但在本机没找到其主目录的工具',
  ],
  'ho.detected': ['Detected', '已检测'],
  'ho.noEntries': ['detected, nothing loaded', '已检测，未载入技能'],
  'ho.globalDir': ['Global', '全局'],
  'ho.projects': ['{n} projects', '{n} 个项目'],
  'ho.project': ['Project', '项目'],
  'ho.sharedBy': ['shared by {list}', '{list} 共用'],
  'ho.undetected': ['{n} tools not detected on this host', '{n} 个工具在本机未检测到'],
  'ho.undetected.hint': [
    'Known to the reporter; no home directory found here. Install one and it appears on the next report.',
    '上报器认识这些工具，但本机没有它们的主目录；装了之后下一次上报就会出现。',
  ],

  // ── topology ───────────────────────────────────────────────────────────
  'to.group.tag': ['Domain', '领域'],
  'to.group.vendor': ['Vendor', '厂商'],
  'to.group.source': ['Source kind', '真源类别'],
  'to.groupBy': ['Group by {by}', '按{by}分组'],
  'to.groupBy.label': ['Grouping', '分组方式'],
  'to.all': ['All skills (by {by})', '全部技能（按{by}）'],
  'to.back': ['← Back', '← 后退'],
  'to.forward': ['Forward →', '前进 →'],
  'to.breadcrumb': ['Breadcrumb', '层级路径'],
  'to.summary': ['{skills} skills · {loads} load sites', '{skills} 个技能 · {loads} 处载入'],
  'to.problemsOnly': ['Problems only', '只看问题'],
  'to.view': ['View', '视图'],
  'to.view.chart': ['Chart', '图'],
  'to.view.table': ['Table', '表格'],
  'to.hint.groups': ['Left column: {by} (click to enter)', '左列：{by}（点击进入）'],
  'to.hint.group': [
    'Left column: skills (click to see where each one is loaded)',
    '左列：技能（点击查看它连到哪里）',
  ],
  'to.hint.skill': [
    'Left column: this skill · right column: each load site',
    '左列：该技能 · 右列：每一处载入',
  ],
  'to.folded': [' · {n} low-traffic skills folded', ' · 已折叠 {n} 个低频技能'],
  'to.foldedNode': ['{n} more skills', '其他 {n} 个技能'],
  'to.empty': ['No matching load relationships.', '没有匹配的载入关系。'],
  'to.col.skill': ['Skill', '技能'],
  'to.col.tool': ['Tool', '工具'],
  'to.col.scope': ['Scope', '作用域'],
  'to.col.kind': ['Link kind', '载入方式'],
  'to.col.count': ['Count', '数量'],
  'to.chart': ['Skill load topology', '技能载入拓扑图'],
  'to.scope.project': ['project · {name}', '项目 · {name}'],
  'to.sharedBy': ['This directory is shared by {list}', '此目录由 {list} 共用'],
  'to.sharedCount': ['shared by {n} tools: {list}', '{n} 个工具共用：{list}'],
  'to.detail.title': ['Actual link locations ({n})', '实际链接位置（{n}）'],
  'to.detail.desc': [
    'The real path of every entry, and what it resolves to.',
    '每一处入口的真实路径，以及它解析到的目标。',
  ],
  'to.hover.count': ['{n} sites', '{n} 处'],
} satisfies Record<string, readonly [string, string]>;

export type MsgKey = keyof typeof M;

function initial(): Lang {
  try {
    const q = new URLSearchParams(window.location.search).get('lang');
    if (q === 'en' || q === 'zh') {
      localStorage.setItem(STORAGE_KEY, q);
      return q;
    }
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved === 'en' || saved === 'zh') return saved;
  } catch {
    /* private mode / storage disabled — English is a fine answer */
  }
  return 'en';
}

let current: Lang = initial();
const listeners = new Set<() => void>();

function applyToDocument() {
  document.documentElement.lang = current === 'zh' ? 'zh-CN' : 'en';
  document.title = t('app.title');
}

export function getLang(): Lang {
  return current;
}

export function setLang(lang: Lang) {
  if (lang === current) return;
  current = lang;
  try {
    localStorage.setItem(STORAGE_KEY, lang);
  } catch {
    /* nothing to do — the choice just will not survive a reload */
  }
  applyToDocument();
  listeners.forEach((fn) => fn());
}

function subscribe(fn: () => void) {
  listeners.add(fn);
  return () => { listeners.delete(fn); };
}

/** Translate. Non-component code may call this directly; components should go
 * through `useT()` so they re-render when the language changes. */
export function t(key: MsgKey, vars?: Record<string, string | number>): string {
  const pair = M[key] as readonly [string, string] | undefined;
  let s = pair ? pair[current === 'zh' ? 1 : 0] : String(key);
  if (vars) {
    for (const [k, v] of Object.entries(vars)) s = s.split(`{${k}}`).join(String(v));
  }
  return s;
}

export function useLang(): Lang {
  return useSyncExternalStore(subscribe, getLang, getLang);
}

/** `const t = useT()` — same signature as `t`, plus a re-render on switch. */
export function useT(): typeof t {
  useLang();
  return t;
}

/** Domain tags: the server stores stable keys (`video`, `cn-social`, …) and the
 * reader sees them in their own language. Unknown tags pass through. */
export function categoryLabel(key: string): string {
  const k = `cat.${key}` as MsgKey;
  return k in M ? t(k) : key;
}

/** A skill's family/vendor is a directory the user named, so it is shown
 * verbatim — a folder called `dev` is theirs, not our "Dev & cloud" tag. Only
 * the three values the server synthesises are translated. */
const VENDOR_KEYS = ['standalone', 'unmanaged', 'external'];

export function vendorLabel(key: string): string {
  return VENDOR_KEYS.includes(key) ? t(`cat.${key}` as MsgKey) : key;
}

applyToDocument();
