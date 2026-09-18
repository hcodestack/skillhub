import { useState } from 'react';
import { Button, Card, Chip, Disclosure, Spinner } from '@heroui/react';
import { agentLabel, fmtRel, useApi } from '../lib/api';
import { useT, type MsgKey } from '../lib/i18n';
import { McpDocToggle, McpStateChip, mcpStateMeta } from '../lib/mcpDoc';
import { ToolIcon } from '../components/ToolIcon';

type McpSkill = {
  uri: string; name: string; description: string;
  files: number; bytes: number; verifiable: string; digest: string;
};
type Declaration = {
  host: string; agent: string; scope: string; project_path: string;
  name: string; has_auth: number;
};
type McpServer = {
  endpoint: string; transport: string;
  server_name: string; server_title: string; server_version: string;
  protocol: string; skills_ext: number; directory_read: number;
  state: string; detail: string;
  skills_count: number; meta_tokens: number; probed_at: number;
  declarations: Declaration[]; skills: McpSkill[];
  agents: string[]; hosts: string[]; has_auth: boolean;
};
type Payload = {
  servers: McpServer[];
  totals: { endpoints: number; serving: number; skills: number;
            meta_tokens: number; unprobed: number };
};

function Tile({ label, value, tone, title }: {
  label: string; value: number | string; tone?: 'warn'; title?: string;
}) {
  return (
    <Card className="min-w-28 flex-1" title={title}>
      <Card.Content className="px-4 py-3">
        <div className={`text-2xl font-semibold tabular-nums ${
          tone === 'warn' ? 'text-amber-600 dark:text-amber-400' : ''}`}>{value}</div>
        <div className="mt-0.5 whitespace-nowrap text-xs text-foreground/60">{label}</div>
      </Card.Content>
    </Card>
  );
}

/* A served skill costs nothing on disk and nothing in context until it is
 * loaded. What it does cost, always, is its name and description — so those
 * are what the row leads with, and the file count sits behind them. */
function SkillRow({ s }: { s: McpSkill }) {
  const t = useT();
  const cls = s.verifiable === 'full'
    ? 'bg-foreground/5 text-foreground/55'
    : 'bg-amber-500/15 text-amber-700 dark:text-amber-300';
  return (
    <li className="border-t border-foreground/5 py-2 first:border-0">
      <div className="flex flex-wrap items-baseline gap-2">
        <span className="font-medium">{s.name}</span>
        <Chip size="sm" className={cls}
              title={s.verifiable === 'full' ? undefined
                : t(`mcp.verifiable.${s.verifiable}.title` as MsgKey)}>
          {t(`mcp.verifiable.${s.verifiable}` as MsgKey)}
        </Chip>
        <span className="tabular-nums text-xs text-foreground/50">
          {s.files < 0 ? t('mcp.dynamic') : t('mcp.files', { n: s.files })}
          {s.bytes > 0 && ` · ${(s.bytes / 1024).toFixed(0)} KB`}
        </span>
      </div>
      <p className="mt-0.5 line-clamp-2 text-xs leading-relaxed text-foreground/70">
        {s.description}
      </p>
      <div className="mt-0.5 truncate font-mono text-[11px] text-foreground/45"
           title={s.uri}>{s.uri}</div>
    </li>
  );
}

function ServerCard({ s }: { s: McpServer }) {
  const t = useT();
  const meta = mcpStateMeta(s.state);
  const title = s.server_title || s.server_name || s.endpoint.replace(/^stdio:/, '');
  return (
    <Card>
      <Card.Content className="flex flex-col gap-2 px-4 py-3">
        <div className="flex flex-row flex-wrap items-center gap-2">
          <span className="h-2.5 w-2.5 shrink-0 rounded-full"
                style={{ background: meta?.color ?? 'var(--sh-link-unrooted, #8a8a90)' }} />
          <span className="truncate font-medium">{title}</span>
          <McpStateChip state={s.state} />
          {s.has_auth && (
            <Chip size="sm" className="bg-foreground/10 text-foreground/60">
              {t('mcp.needsAuth')}
            </Chip>
          )}
          {s.directory_read > 0 && (
            <Chip size="sm" className="bg-foreground/10 text-foreground/60">
              {t('mcp.dirRead')}
            </Chip>
          )}
        </div>

        <div className="break-all font-mono text-xs text-foreground/60">{s.endpoint}</div>

        {s.detail && (
          <div className="text-xs leading-relaxed text-foreground/60">{s.detail}</div>
        )}

        <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1 text-xs text-foreground/60">
          {s.skills_count > 0 && (
            <span className="text-foreground/80">
              {t('mcp.skills.n', { n: s.skills_count })}
              <span className="ml-1 tabular-nums">~{s.meta_tokens} tok</span>
            </span>
          )}
          {s.protocol && <span>{t('mcp.protocol')} {s.protocol}</span>}
          {s.server_version && <span className="font-mono">v{s.server_version}</span>}
          {s.probed_at > 0 && (
            <span>{t('mcp.lastProbe', {
              when: fmtRel(new Date(s.probed_at * 1000).toISOString()) })}</span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-1.5 border-t border-foreground/10 pt-2">
          <span className="mr-1 text-xs text-foreground/60">{t('mcp.declaredBy')}</span>
          {s.agents.map((a) => (
            <Chip key={a} size="sm" className="gap-1 bg-foreground/5 text-foreground/70">
              <ToolIcon agent={a} size={12} />
              {agentLabel(a)}
            </Chip>
          ))}
          <span className="text-xs text-foreground/45">
            {s.declarations.map((d) => d.name).filter((v, i, arr) => arr.indexOf(v) === i)
              .slice(0, 3).join(' · ')}
          </span>
        </div>

        {s.skills.length > 0 && (
          <Disclosure className="rounded-lg border border-foreground/10">
            <Disclosure.Heading>
              <Disclosure.Trigger className="w-full px-3 py-1.5">
                <span className="flex w-full items-center gap-2 text-left text-xs font-medium">
                  {t('mcp.skills.show')}
                  <span className="tabular-nums text-foreground/50">{s.skills.length}</span>
                </span>
                <Disclosure.Indicator />
              </Disclosure.Trigger>
            </Disclosure.Heading>
            <Disclosure.Content>
              <ul className="max-h-96 overflow-y-auto px-3 pb-2">
                {s.skills.map((sk) => <SkillRow key={sk.uri} s={sk} />)}
              </ul>
            </Disclosure.Content>
          </Disclosure>
        )}
      </Card.Content>
    </Card>
  );
}

export default function Mcp() {
  const t = useT();
  const { data, reload } = useApi<Payload>('/mcp/servers');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const reprobe = async () => {
    setBusy(true); setErr('');
    try {
      const res = await fetch('/api/v1/mcp/probe', { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await reload();
    } catch (e) {
      setErr(t('mcp.probeFailed', { err: String(e) }));
    } finally {
      setBusy(false);
    }
  };

  if (!data) {
    return <div className="flex justify-center py-20"><Spinner aria-label={t('common.loading')} /></div>;
  }
  if (!data.servers.length) {
    return <p className="py-16 text-center text-foreground/60">{t('mcp.none')}</p>;
  }

  // serving first, then the states that need a look, then the deliberate refusals
  const rank = (s: McpServer) => (
    { served: 0, empty: 1, unreachable: 2, 'no-extension': 3, auth: 4, declared: 5 }
    [s.state as string] ?? 6);
  const servers = [...data.servers].sort(
    (a, b) => rank(a) - rank(b) || b.skills_count - a.skills_count
      || a.endpoint.localeCompare(b.endpoint));
  const { totals } = data;

  return (
    <div className="flex flex-col gap-5">
      <p className="max-w-3xl text-sm leading-relaxed text-foreground/70">{t('mcp.lede')}</p>

      <div className="flex flex-wrap gap-3">
        <Tile label={t('mcp.tile.servers')} value={totals.endpoints} />
        <Tile label={t('mcp.tile.serving')} value={totals.serving} />
        <Tile label={t('mcp.tile.skills')} value={totals.skills} />
        <Tile label={t('mcp.tile.tokens')} value={`~${totals.meta_tokens}`}
              title={t('mcp.tile.tokens.title')} />
        <Tile label={t('mcp.tile.unprobed')} value={totals.unprobed}
              tone={totals.unprobed > 0 ? 'warn' : undefined} />
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <McpDocToggle />
        <Button size="sm" className="ml-auto" isDisabled={busy} onPress={reprobe}>
          {busy ? t('mcp.reprobing') : t('mcp.reprobe')}
        </Button>
        {err && <span className="w-full text-right text-xs text-red-600 dark:text-red-400">{err}</span>}
      </div>

      <div className="grid grid-cols-1 gap-3 lg:grid-cols-2">
        {servers.map((s) => <ServerCard key={s.endpoint} s={s} />)}
      </div>
    </div>
  );
}
