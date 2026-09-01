import { useEffect, useState } from 'react';
import { Card, Chip, Spinner } from '@heroui/react';
import { agentLabel, fmtRel, useApi, type HealthSection } from '../lib/api';
import { LinkDocToggle } from '../lib/linkDoc';
import { AgentChip } from '../components/AgentChips';

const SEV_CLASS: Record<string, string> = {
  error: 'bg-red-500/15 text-red-700 dark:text-red-300',
  warn: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  info: 'bg-foreground/10 text-foreground/60',
};
const SEV_LABEL: Record<string, string> = { error: '异常', warn: '关注', info: '提示' };

const JOB_STATUS: Record<string, { label: string; cls: string }> = {
  ok: { label: '正常', cls: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300' },
  failed: { label: '失败', cls: 'bg-red-500/15 text-red-700 dark:text-red-300' },
  stuck: { label: '卡住', cls: 'bg-red-500/15 text-red-700 dark:text-red-300' },
  running: { label: '运行中', cls: 'bg-sky-500/15 text-sky-700 dark:text-sky-300' },
  never: { label: '未运行', cls: 'bg-foreground/10 text-foreground/60' },
};

function fmtDur(s: number): string {
  if (s < 1) return '<1 秒';
  if (s < 60) return `${s} 秒`;
  return `${Math.floor(s / 60)} 分 ${s % 60} 秒`;
}

function Items({ section }: { section: HealthSection }) {
  const items = section.items as Record<string, any>[];

  // Jobs render even when nothing is wrong: "nothing to report" and "the job
  // never ran" look identical everywhere else on this page, and telling them
  // apart is the whole point of the section.
  if (section.key === 'background_jobs') {
    return (
      <ul className="flex flex-col gap-2">
        {items.map((j, i) => {
          const st = JOB_STATUS[String(j.status)] ?? JOB_STATUS.never;
          const running = j.status === 'running' || j.status === 'stuck';
          return (
            <li key={i} className="text-sm">
              <div className="flex flex-wrap items-center gap-1.5">
                <Chip size="sm" className={st.cls}>{st.label}</Chip>
                <span className="font-medium">{String(j.label)}</span>
                {j.started_at ? (
                  <span className="text-xs text-foreground/60">
                    {running ? '已运行' : '结束于'}{' '}
                    {running
                      ? fmtDur(Number(j.duration_s))
                      : fmtRel(new Date(Number(j.finished_at) * 1000).toISOString())}
                    {!running && Number(j.duration_s) > 0
                      && `，耗时 ${fmtDur(Number(j.duration_s))}`}
                  </span>
                ) : null}
              </div>
              {j.error ? (
                <div className="mt-0.5 break-all font-mono text-xs text-red-600 dark:text-red-400">
                  {String(j.error)}
                </div>
              ) : j.detail ? (
                <div className="mt-0.5 text-xs text-foreground/60">{String(j.detail)}</div>
              ) : null}
            </li>
          );
        })}
      </ul>
    );
  }

  if (!items.length) {
    return <p className="text-sm text-foreground/60">无</p>;
  }
  if (section.key === 'idle_skills') {
    const shown = items.slice(0, 80);
    return (
      <div className="flex flex-wrap gap-1">
        {shown.map((it) => (
          <span key={String(it.id)} className="rounded bg-foreground/5 px-1.5 py-0.5 font-mono text-xs text-foreground/60">
            {String(it.id)}
          </span>
        ))}
        {items.length > shown.length && (
          <span className="px-1.5 py-0.5 text-xs text-foreground/60">
            +{items.length - shown.length} 更多
          </span>
        )}
      </div>
    );
  }
  if (section.key === 'thin_descriptions' || section.key === 'oversized_bodies'
      || section.key === 'unindexed_skills') {
    return (
      <ul className="flex flex-col gap-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex flex-wrap items-baseline gap-2 text-sm">
            <span className="font-mono text-xs">{String(it.id ?? it.path ?? '')}</span>
            {it.chars != null && (
              <span className="tabular-nums text-foreground/60">{String(it.chars)} 字符</span>
            )}
            {it.lines != null && (
              <span className="tabular-nums text-foreground/60">{String(it.lines)} 行</span>
            )}
          </li>
        ))}
      </ul>
    );
  }
  if (section.key === 'safety_high') {
    return (
      <ul className="flex flex-col gap-2">
        {items.map((it, i) => (
          <li key={i} className="border-t border-foreground/5 pt-2 first:border-0 text-sm">
            <div className="flex flex-wrap items-baseline gap-2">
              <span className="font-medium">{String(it.id)}</span>
              <span className="text-xs text-foreground/60">{String(it.category)}</span>
              <span className="font-mono text-xs text-foreground/60">{String(it.where)}</span>
            </div>
            <div className="text-foreground/75">{String(it.description)}</div>
            <code className="mt-0.5 block break-all rounded bg-foreground/5 px-2 py-1 text-xs">
              {String(it.excerpt)}
            </code>
          </li>
        ))}
      </ul>
    );
  }
  if (section.key === 'duplicate_copies') {
    return (
      <ul className="flex flex-col gap-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex flex-wrap items-baseline gap-2 text-sm">
            <span className="font-medium">{String(it.entry_name)}</span>
            <span className="tabular-nums text-foreground/60">{String(it.copies)} 份副本</span>
            {it.drifted ? (
              <Chip size="sm" className="bg-amber-500/15 text-amber-700 dark:text-amber-300">
                内容不一致（{String(it.variants)} 种）
              </Chip>
            ) : (
              <Chip size="sm" className="bg-foreground/10 text-foreground/60">内容一致</Chip>
            )}
            <span className="text-xs text-foreground/60">
              {String(it.agents ?? '').split(',').map((a) => agentLabel(a)).join(' · ')}
            </span>
          </li>
        ))}
      </ul>
    );
  }
  if (section.key === 'unresolved_usage') {
    return (
      <ul className="flex flex-col gap-1.5">
        {items.map((it, i) => (
          <li key={i} className="flex flex-wrap items-baseline gap-2 text-sm">
            <span className="font-mono">{String(it.skill_key)}</span>
            <span className="tabular-nums text-foreground/60">{String(it.n)} 次</span>
            <span className="text-xs text-foreground/60">{String(it.agents ?? '')}</span>
            <span className="text-xs text-foreground/60">最近 {fmtRel(it.last as string)}</span>
          </li>
        ))}
      </ul>
    );
  }
  return (
    <ul className="flex flex-col gap-2">
      {items.map((it, i) => (
        <li key={i} className="text-sm">
          <div className="flex flex-wrap items-center gap-1.5">
            {it.agent != null && <AgentChip agent={String(it.agent)} />}
            {it.scope != null && (
              <Chip size="sm" className="bg-foreground/10">
                {it.scope === 'global' ? '全局' : '项目'}
              </Chip>
            )}
            <span className="font-medium">{String(it.entry_name ?? '')}</span>
            <span className="text-xs text-foreground/60">{String(it.host ?? '')}</span>
          </div>
          <div className="mt-0.5 break-all font-mono text-xs text-foreground/60">
            {String(it.project_path || it.entry_path || '')}
          </div>
        </li>
      ))}
    </ul>
  );
}

function hashSection(): string {
  const [tab, sec] = window.location.hash.slice(1).split('/');
  return tab === 'health' && sec ? sec : '';
}

export default function Health() {
  const { data } = useApi<{ sections: HealthSection[] }>('/health/findings');
  const sections = data?.sections ?? null;

  // Progressive disclosure: twelve fully expanded item lists made the page a
  // wall (~120 KB of it) where nothing stood out. Headlines are always
  // visible — counts and severity answer "is anything wrong" at a glance —
  // and a section opens when it is red, when the user asks, or when a deep
  // link (#health/<key>, e.g. from an overview tile) targets it.
  const [open, setOpen] = useState<Record<string, boolean>>(() => {
    const target = hashSection();
    return target ? { [target]: true } : {};
  });
  const toggled = (s: HealthSection) =>
    open[s.key] ?? (s.severity === 'error' && s.count > 0);

  useEffect(() => {
    const follow = () => {
      const target = hashSection();
      if (!target) return;
      setOpen((o) => ({ ...o, [target]: true }));
      // wait a frame so the section exists before scrolling to it
      requestAnimationFrame(() => {
        document.getElementById(`sec-${target}`)?.scrollIntoView({ block: 'start', behavior: 'smooth' });
      });
    };
    follow();
    window.addEventListener('hashchange', follow);
    return () => window.removeEventListener('hashchange', follow);
  }, [sections]);

  if (!sections) {
    return <div className="flex justify-center py-20"><Spinner aria-label="加载中" /></div>;
  }
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-foreground/60">
          下面各节反复出现「软链 / 仓库自带 / 散落实体 / 断链」——
        </span>
        <LinkDocToggle />
        {/* findings that never leave the dashboard are trivia: the report is a
            work order you can archive or hand to an agent, the script executes
            the provably-safe part on the machine the files actually live on */}
        <span className="ml-auto flex items-center gap-2">
          <a className="rounded-md border border-foreground/15 px-2 py-0.5 text-xs text-foreground/70 transition-colors hover:border-foreground/30 hover:text-foreground"
             href="/api/v1/report/governance.md" download="skillhub-治理报告.md">
            导出治理报告
          </a>
          <a className="rounded-md border border-foreground/15 px-2 py-0.5 text-xs text-foreground/70 transition-colors hover:border-foreground/30 hover:text-foreground"
             href="/api/v1/report/remediation.sh" download="skillhub-清理脚本.sh"
             title="只有「删除仍悬空的软链」是未注释的；其余操作以注释给出，审阅后自行放开">
            下载清理脚本
          </a>
        </span>
      </div>
      {sections.map((s) => {
        const expanded = toggled(s);
        const empty = s.items.length === 0;
        return (
          <Card key={s.key} id={`sec-${s.key}`} className="scroll-mt-4">
            <Card.Header className={expanded ? 'pb-2' : 'pb-4'}>
              <button
                type="button"
                className="flex w-full items-center gap-2 text-left"
                aria-expanded={expanded}
                onClick={() => setOpen((o) => ({ ...o, [s.key]: !expanded }))}
              >
                <Chip size="sm" className={SEV_CLASS[s.severity] ?? SEV_CLASS.info}>
                  {SEV_LABEL[s.severity] ?? s.severity}
                </Chip>
                <Card.Title className="text-base">{s.title}</Card.Title>
                <span className="tabular-nums text-sm text-foreground/60">{s.count}</span>
                <span aria-hidden className="ml-auto text-foreground/60">
                  {expanded ? '▾' : '▸'}
                </span>
              </button>
              <Card.Description>{s.hint}</Card.Description>
            </Card.Header>
            {expanded && !empty && (
              <Card.Content>
                <Items section={s} />
              </Card.Content>
            )}
          </Card>
        );
      })}
    </div>
  );
}
