import { useEffect, useMemo, useState } from 'react';
import { Button, Chip, Disclosure, Drawer, Spinner } from '@heroui/react';
import {
  agentLabel, api, fmtRel, SOURCE_LABEL, UPDATE_LABEL,
  type Install, type SkillItem, type UsageEvent,
} from '../lib/api';
import { AgentChip } from './AgentChips';
import { CopyButton, PathChain, PathText, prettyPath } from '../lib/paths';

const LINK_LABEL: Record<string, string> = {
  symlink: '软链', entity: '散落实体', vendored: '仓库自带', broken: '断链',
};
const LINK_NOTE: Record<string, string> = {
  symlink: '指向库内真源，更新一次处处生效——目标状态，无需处理',
  vendored: '项目仓库自带（作者提交进去的，克隆时就有）——随该仓库 git pull 更新，无需清理或纳管',
  entity: '独立拷贝：改库内真源不会同步到它，多份副本会漂移——建议入库后换成 skill load 软链',
  broken: '软链目标已不存在（真源被移动或删除）——不再用就删掉，还要用就重新 skill load',
};
const LINK_CLASS: Record<string, string> = {
  entity: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  vendored: 'bg-sky-500/15 text-sky-700 dark:text-sky-300',
  broken: 'bg-red-500/15 text-red-700 dark:text-red-300',
  symlink: 'bg-foreground/10 text-foreground/65',
};

// a copy committed inside someone's repo is a different finding from a copy
// nobody owns, so the chip has to say which
function linkKind(ins: Install): string {
  if (ins.link_type !== 'entity') return ins.link_type;
  return ins.vcs === 'vendored' ? 'vendored' : 'entity';
}
const SEV_CLASS: Record<string, string> = {
  high: 'bg-red-500/15 text-red-700 dark:text-red-300',
  medium: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  low: 'bg-foreground/10 text-foreground/60',
};
const SEV_LABEL: Record<string, string> = { high: '高危', medium: '中', low: '低' };

const UPDATE_CLASS: Record<string, string> = {
  behind: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  moved: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  current: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
};

// Evaluation is deliberately NOT done here. Anthropic's skill-creator already
// ships graders, a comparator and an eval viewer, and its method (run the task
// with and without the skill, then score against assertions) needs real task
// runs — not something a dashboard should reimplement. We just hand over a
// ready-to-run prompt so the work happens where the tooling already lives.
function evalPrompt(item: SkillItem): string {
  const p = item.library_path || item.installs[0]?.target_path
    || item.installs[0]?.entry_path || '';
  return [
    '使用 skill-creator 技能，评估这个技能并给出改进建议：',
    `- 技能 id：${item.id ?? item.name}`,
    p ? `- 路径：${p}` : '',
    '请重点看：description 能否可靠触发（是否写清了「何时用」）、',
    'SKILL.md 正文长度与结构是否合理、是否该把内容下沉到 references/。',
    '如果值得，再设计 2-3 个测试用例并跑一轮带技能 vs 基线的对比。',
  ].filter(Boolean).join('\n');
}

function Section({ title, count, children, defaultExpanded = true, hint }: {
  title: string; count?: number; children: React.ReactNode;
  defaultExpanded?: boolean; hint?: string;
}) {
  return (
    <Disclosure defaultExpanded={defaultExpanded}
                className="rounded-lg border border-foreground/10">
      <Disclosure.Heading>
        <Disclosure.Trigger className="w-full px-3 py-2">
          <span className="flex w-full items-center gap-2 text-left">
            <span className="text-sm font-medium">{title}</span>
            {count != null && (
              <span className="tabular-nums text-xs text-foreground/60">{count}</span>
            )}
            {hint && <span className="truncate text-xs text-foreground/60">{hint}</span>}
          </span>
          <Disclosure.Indicator />
        </Disclosure.Trigger>
      </Disclosure.Heading>
      <Disclosure.Content>
        <div className="px-3 pb-3">{children}</div>
      </Disclosure.Content>
    </Disclosure>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5 py-1">
      <span className="w-20 shrink-0 text-xs text-foreground/60">{label}</span>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

function InstallRow({ ins, libraryRoot }: { ins: Install; libraryRoot: string }) {
  return (
    <li className="border-t border-foreground/5 py-2 first:border-0">
      <div className="mb-1 flex flex-wrap items-center gap-1.5">
        <AgentChip agent={ins.agent} />
        <Chip size="sm" className={ins.scope === 'global'
          ? 'bg-violet-500/15 text-violet-700 dark:text-violet-300'
          : 'bg-foreground/10 text-foreground/65'}>
          {ins.scope === 'global' ? '全局' : '项目'}
        </Chip>
        <Chip size="sm" className={LINK_CLASS[linkKind(ins)] ?? LINK_CLASS.symlink}
              title={LINK_NOTE[linkKind(ins)]}>
          {LINK_LABEL[linkKind(ins)] ?? ins.link_type}
        </Chip>
        {ins.scope === 'project' && ins.project_path && (
          <span className="truncate text-xs text-foreground/60"
                title={ins.project_path}>
            {ins.project_path.split('/').pop()}
          </span>
        )}
      </div>
      <PathChain from={ins.entry_path} to={ins.target_path} libraryRoot={libraryRoot} />
      {ins.shared_with && (
        <div className="mt-1 text-xs text-foreground/60">
          此目录同时服务：{ins.shared_with}
        </div>
      )}
    </li>
  );
}

export function SkillDrawer({ item, libraryRoot = '', onClose }: {
  item: SkillItem | null; libraryRoot?: string; onClose: () => void;
}) {
  const [events, setEvents] = useState<UsageEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!item) return;
    setEvents([]); setTotal(0); setLoading(true);
    api<{ total: number; events: UsageEvent[] }>(
      `/skills/events?k=${encodeURIComponent(item.key)}&limit=50`)
      .then((d) => { setEvents(d.events); setTotal(d.total); })
      .finally(() => setLoading(false));
  }, [item?.key]);

  const loadMore = () => {
    if (!item) return;
    api<{ total: number; events: UsageEvent[] }>(
      `/skills/events?k=${encodeURIComponent(item.key)}&limit=50&offset=${events.length}`)
      .then((d) => setEvents((e) => [...e, ...d.events]));
  };

  // group by machine first: with several hosts a flat list stops being readable
  const byHost = useMemo(() => {
    const m = new Map<string, Install[]>();
    for (const ins of item?.installs ?? []) {
      if (!m.has(ins.host)) m.set(ins.host, []);
      m.get(ins.host)!.push(ins);
    }
    for (const list of m.values()) {
      list.sort((a, b) => (a.scope === b.scope ? a.agent.localeCompare(b.agent)
        : a.scope === 'global' ? -1 : 1));
    }
    return [...m.entries()];
  }, [item]);

  const upd = item?.update;
  const srcPath = item?.library_path
    || item?.installs.find((i) => i.target_path)?.target_path || '';

  return (
    <Drawer isOpen={!!item} onOpenChange={(o: boolean) => { if (!o) onClose(); }}>
      {/* Right placement + a narrower dialog: this drawer annotates the table
          row the user just clicked, and it used to slide in from the LEFT and
          cover exactly that table. An inspection panel that hides the thing it
          inspects forces a close-reopen cycle per skill (NN/g: avoid modals for
          decisions that need context the modal hides). Right side keeps the
          name column — the part you compare against — visible. */}
      <Drawer.Backdrop>
        <Drawer.Content placement="right">
          <Drawer.Dialog className="w-full max-w-xl">
            <Drawer.CloseTrigger />
            <Drawer.Header>
              <Drawer.Heading>{item?.name ?? ''}</Drawer.Heading>
            </Drawer.Header>
            <Drawer.Body>
              {item && (
                <div className="flex flex-col gap-3 pb-6">
                  {/* identity */}
                  <div className="flex flex-wrap items-center gap-1.5">
                    <Chip size="sm" className="bg-foreground/10">
                      {SOURCE_LABEL[item.source] ?? item.source}
                    </Chip>
                    {item.category && (
                      <Chip size="sm" className="bg-foreground/10">{item.category}</Chip>
                    )}
                    {item.tags.map((t) => (
                      <Chip key={t} size="sm"
                            className="bg-sky-500/15 text-sky-700 dark:text-sky-300">{t}</Chip>
                    ))}
                    {item.vetting?.top_severity === 'high' && (
                      <Chip size="sm" className={SEV_CLASS.high}>安全高危</Chip>
                    )}
                    {upd && UPDATE_LABEL[upd.state] && (
                      <Chip size="sm" className={UPDATE_CLASS[upd.state] ?? 'bg-foreground/10'}>
                        {UPDATE_LABEL[upd.state]}
                      </Chip>
                    )}
                  </div>
                  {item.id && item.id !== item.name && (
                    <div className="font-mono text-xs text-foreground/60">{item.id}</div>
                  )}
                  <p className="text-sm leading-relaxed text-foreground/80">
                    {item.description || '（无描述）'}
                  </p>

                  <Section title="真源" hint={item.in_library ? '' : '未纳管，无库内真源'}>
                    {srcPath ? (
                      <>
                        <Field label="库内路径">
                          <div className="flex items-start gap-2">
                            <PathText path={srcPath} libraryRoot={libraryRoot} />
                            <CopyButton text={srcPath} />
                          </div>
                        </Field>
                        {upd?.origin && (
                          <Field label="上游">
                            <a href={upd.origin} target="_blank" rel="noreferrer"
                               className="break-all text-xs text-sky-600 underline dark:text-sky-400">
                              {upd.origin}
                            </a>
                            {upd.local_ref && (
                              <span className="ml-2 font-mono text-xs text-foreground/60">
                                {upd.local_ref}{upd.remote_ref && upd.state === 'behind'
                                  ? ` → ${upd.remote_ref}` : ''}
                              </span>
                            )}
                          </Field>
                        )}
                        {(item.body_lines ?? 0) > 0 && (
                          <Field label="体量">
                            <span className="text-xs text-foreground/65">
                              SKILL.md {item.body_lines} 行 · 描述 {item.desc_chars} 字符
                              {(item.body_lines ?? 0) > 500 && (
                                <span className="ml-2 text-amber-600 dark:text-amber-400">
                                  超过官方建议的 500 行
                                </span>
                              )}
                            </span>
                          </Field>
                        )}
                      </>
                    ) : (
                      <p className="text-sm text-foreground/60">
                        这个技能只存在于工具入口目录，库内没有对应真源。
                      </p>
                    )}
                  </Section>

                  {item.vetting && item.vetting.count > 0 && (
                    <Section title="安全审查" count={item.vetting.count}
                      hint={item.vetting.top_severity === 'high' ? '含高危信号' : ''}
                      defaultExpanded={item.vetting.top_severity === 'high'}>
                      <p className="mb-2 text-xs text-foreground/60">
                        确定性规则命中，是信号不是判决——联网技能里出现 curl 本就正常，
                        但值得你亲眼看一眼这几行。
                      </p>
                      <ul className="flex flex-col gap-2">
                        {item.vetting.findings.map((f, i) => (
                          <li key={i} className="border-t border-foreground/5 pt-2 first:border-0">
                            <div className="flex flex-wrap items-center gap-1.5">
                              <Chip size="sm" className={SEV_CLASS[f.severity] ?? SEV_CLASS.low}>
                                {SEV_LABEL[f.severity] ?? f.severity}
                              </Chip>
                              <span className="text-xs text-foreground/60">{f.category}</span>
                              <span className="font-mono text-xs text-foreground/60">
                                {f.file}:{f.line}
                              </span>
                            </div>
                            <div className="mt-0.5 text-sm text-foreground/80">{f.description}</div>
                            <code className="mt-1 block break-all rounded bg-foreground/5 px-2 py-1 text-xs">
                              {f.excerpt}
                            </code>
                          </li>
                        ))}
                      </ul>
                    </Section>
                  )}

                  <Section title="载入位置" count={item.installs.length}>
                    {item.installs.length === 0 ? (
                      <p className="text-sm text-foreground/60">当前未载入到任何入口。</p>
                    ) : (
                      <div className="flex flex-col gap-3">
                        {byHost.map(([host, list]) => (
                          <div key={host}>
                            <div className="mb-0.5 flex items-baseline gap-2">
                              <span className="text-xs font-medium text-foreground/70">{host}</span>
                              <span className="text-xs text-foreground/60">{list.length} 处</span>
                            </div>
                            <ul className="rounded-md bg-foreground/[0.03] px-2.5">
                              {list.map((ins, i) => (
                                <InstallRow key={i} ins={ins} libraryRoot={libraryRoot} />
                              ))}
                            </ul>
                          </div>
                        ))}
                      </div>
                    )}
                  </Section>

                  <Section title="调用记录" count={total} defaultExpanded={false}
                           hint={item.usage.last ? `最近 ${fmtRel(item.usage.last)}` : '暂无调用'}>
                    {loading ? (
                      <Spinner aria-label="加载中" />
                    ) : events.length === 0 ? (
                      <p className="text-sm text-foreground/60">暂无调用记录。</p>
                    ) : (
                      <ul className="flex flex-col gap-1">
                        {events.map((e, i) => (
                          <li key={i}
                              className="flex items-baseline gap-2 border-b border-foreground/5 pb-1 text-sm">
                            <span className="w-32 shrink-0 text-xs text-foreground/60">
                              {e.ts.replace('T', ' ')}
                            </span>
                            <AgentChip agent={e.agent} />
                            <span className="truncate text-xs text-foreground/60"
                                  title={e.project || e.source}>
                              {e.project ? prettyPath(e.project).split('/').pop() : e.source}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                    {events.length < total && (
                      <Button size="sm" variant="ghost" className="mt-2" onPress={loadMore}>
                        加载更多（{events.length}/{total}）
                      </Button>
                    )}
                  </Section>

                  <div className="flex flex-wrap items-center gap-2 pt-1">
                    <CopyButton text={evalPrompt(item)} label="复制评估提示词" />
                    <span className="text-xs text-foreground/60">
                      粘进 Claude Code 用 skill-creator 评估（本看板不内置模型）
                    </span>
                  </div>
                </div>
              )}
            </Drawer.Body>
          </Drawer.Dialog>
        </Drawer.Content>
      </Drawer.Backdrop>
    </Drawer>
  );
}
