import { Card, Chip, Disclosure, Spinner } from '@heroui/react';
import {
  AGENT_LABEL, agentLabel, fmtRel, isSharedDir, useApi, type HostAgent, type HostRow, type Tiles,
} from '../lib/api';
import { useT } from '../lib/i18n';
import { PathText } from '../lib/paths';
import { ToolIcon } from '../components/ToolIcon';

/* One card per tool the reporter detected on the host — where it reads its
 * global skills from, which projects it is loaded into, and how many entries
 * — with the tools it did NOT find folded away underneath. The old page was
 * a list of counts; this answers the question people actually bring here:
 * "which of my tools does the hub see, and where does each one look?"
 * (Layout after skills-hub's Tools page.) */
function ToolCard({ a, libraryRoot }: { a: HostAgent; libraryRoot: string }) {
  const t = useT();
  const shown = a.project_dirs.slice(0, 3);
  return (
    <Card>
      <Card.Content className="flex flex-col gap-2 px-4 py-3">
        <div className="flex flex-row items-center gap-2">
          <ToolIcon agent={a.agent} size={22} />
          <span className="truncate font-medium">{agentLabel(a.agent)}</span>
          <Chip size="sm" className="ml-auto shrink-0 bg-emerald-500/15 text-emerald-700 dark:text-emerald-300">
            {t('ho.detected')}
          </Chip>
        </div>
        {isSharedDir(a.agent) && a.shared_with && (
          <div className="text-xs text-foreground/60">{t('ho.sharedBy', { list: a.shared_with })}</div>
        )}
        <div className="text-sm tabular-nums text-foreground/70">
          {t('ho.entries', { n: a.entries, g: a.global_entries, p: a.project_entries })}
        </div>
        {a.global_dir && (
          <div className="flex items-baseline gap-2">
            <span className="w-14 shrink-0 text-xs text-foreground/60">{t('ho.globalDir')}</span>
            <PathText path={a.global_dir} libraryRoot={libraryRoot} />
          </div>
        )}
        {a.project_dirs.length > 0 && (
          <div className="flex items-baseline gap-2">
            <span className="w-14 shrink-0 text-xs text-foreground/60">
              {a.project_dirs.length > 1 ? t('ho.projects', { n: a.project_dirs.length }) : t('ho.project')}
            </span>
            <div className="flex min-w-0 flex-wrap gap-x-2 gap-y-0.5">
              {shown.map((p) => (
                <span key={p} title={p} className="font-mono text-xs text-foreground/70">
                  {p.split('/').filter(Boolean).pop()}
                </span>
              ))}
              {a.project_dirs.length > shown.length && (
                <span className="text-xs text-foreground/50"
                      title={a.project_dirs.slice(3).join('\n')}>
                  +{a.project_dirs.length - shown.length}
                </span>
              )}
            </div>
          </div>
        )}
      </Card.Content>
    </Card>
  );
}

function Tile({ label, value, title }: { label: string; value: number; title?: string }) {
  return (
    <Card className="min-w-28 flex-1" title={title}>
      <Card.Content className="px-4 py-3">
        <div className="text-2xl font-semibold tabular-nums">{value}</div>
        <div className="mt-0.5 whitespace-nowrap text-xs text-foreground/60">{label}</div>
      </Card.Content>
    </Card>
  );
}

function Host({ h, libraryRoot }: { h: HostRow; libraryRoot: string }) {
  const t = useT();
  const withEntries = new Map(h.agents.map((a) => [a.agent, a]));
  // detected tools with nothing loaded still get a card — that they are
  // present but empty is the finding
  const detected = h.detected_agents.map((k) => withEntries.get(k) ?? {
    agent: k, entries: 0, global_entries: 0, project_entries: 0,
    global_dir: '', project_dirs: [], shared_with: '',
  });
  const known = Object.keys(AGENT_LABEL);
  const undetected = known.filter((k) => !h.detected_agents.includes(k));
  const entries = h.agents.reduce((n, a) => n + a.entries, 0);
  return (
    <section className="flex flex-col gap-4">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-lg font-semibold">{h.id}</h2>
        <span className="text-sm text-foreground/60">
          {h.os} · {t('ho.lastReport', { when: fmtRel(h.last_report_at) })}
          {' · '}{t('ho.total')} <span className="tabular-nums">{h.events_total}</span>
        </span>
      </div>
      <div className="flex flex-wrap gap-3">
        <Tile label={t('ho.tile.detected')} value={detected.length} />
        <Tile label={t('ho.tile.loaded')} value={h.agents.length} />
        <Tile label={t('ho.tile.entries')} value={entries} />
        <Tile label={t('ho.tile.undetected')} value={undetected.length}
              title={t('ho.tile.undetected.title')} />
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
        {detected.map((a) => (
          a.entries > 0
            ? <ToolCard key={a.agent} a={a} libraryRoot={libraryRoot} />
            : (
              <Card key={a.agent} className="border-dashed">
                <Card.Content className="flex flex-row items-center gap-2 px-4 py-3">
                  <ToolIcon agent={a.agent} size={22} className="opacity-70" />
                  <span className="font-medium text-foreground/70">{agentLabel(a.agent)}</span>
                  <span className="ml-auto text-xs text-foreground/50">{t('ho.noEntries')}</span>
                </Card.Content>
              </Card>
            )
        ))}
      </div>
      {undetected.length > 0 && (
        <Disclosure className="rounded-lg border border-foreground/10">
          <Disclosure.Heading>
            <Disclosure.Trigger className="w-full px-3 py-2">
              <span className="flex w-full items-center gap-2 text-left text-sm">
                <span className="font-medium">{t('ho.undetected', { n: undetected.length })}</span>
              </span>
              <Disclosure.Indicator />
            </Disclosure.Trigger>
          </Disclosure.Heading>
          <Disclosure.Content>
            <div className="px-3 pb-3">
              <p className="mb-2 text-xs text-foreground/60">{t('ho.undetected.hint')}</p>
              <div className="flex flex-wrap gap-1.5">
                {undetected.map((k) => (
                  <Chip key={k} size="sm" className="gap-1 bg-foreground/5 text-foreground/60">
                    <ToolIcon agent={k} size={12} className="opacity-60 grayscale" />
                    {agentLabel(k)}
                  </Chip>
                ))}
              </div>
            </div>
          </Disclosure.Content>
        </Disclosure>
      )}
    </section>
  );
}

export default function Hosts() {
  const t = useT();
  const { data } = useApi<{ hosts: HostRow[] }>('/hosts');
  const { data: tiles } = useApi<Tiles>('/stats/tiles');
  const hosts = data?.hosts ?? null;

  if (!hosts) {
    return <div className="flex justify-center py-20"><Spinner aria-label={t('common.loading')} /></div>;
  }
  if (!hosts.length) {
    return <p className="py-16 text-center text-foreground/60">{t('ho.none')}</p>;
  }
  return (
    <div className="flex flex-col gap-8">
      {hosts.map((h) => <Host key={h.id} h={h} libraryRoot={tiles?.library_root ?? ''} />)}
    </div>
  );
}
