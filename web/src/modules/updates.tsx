import { useState } from 'react';
import { Button, Card, Chip, Spinner } from '@heroui/react';
import { fmtRel, updateLabel, useApi, type SourceRow } from '../lib/api';
import { useT } from '../lib/i18n';

const STATE_CLASS: Record<string, string> = {
  behind: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  moved: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  tracked: 'bg-foreground/10 text-foreground/60',
  current: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  installer: 'bg-sky-500/15 text-sky-700 dark:text-sky-300',
  error: 'bg-red-500/15 text-red-700 dark:text-red-300',
  unknown: 'bg-foreground/10 text-foreground/60',
};

type Payload = { items: SourceRow[]; library_total: number; untraced: number };

function UpdateButton({ row, onDone }: { row: SourceRow; onDone: () => void }) {
  const t = useT();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const run = async () => {
    setBusy(true); setMsg('');
    try {
      const res = await fetch('/api/v1/sources/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ skill_id: row.skill_id }),
      });
      const d = await res.json();
      if (d.ok) {
        setMsg(d.changed
          ? t('up.done', { from: d.from, to: d.to, note: d.note ? ' — ' + d.note : '' })
          : t('up.alreadyCurrent'));
        onDone();
      } else {
        setMsg(t('up.failed', { err: d.error }));
      }
    } catch (e) {
      setMsg(t('up.requestFailed', { err: String(e) }));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="mt-1.5">
      <Button size="sm" isDisabled={busy} onPress={run}>
        {busy ? t('up.button.busy') : t('up.button')}
      </Button>
      {msg && <span className="ml-2 text-xs text-foreground/70">{msg}</span>}
    </div>
  );
}

function Cmd({ cmd }: { cmd: string }) {
  const t = useT();
  const [copied, setCopied] = useState(false);
  if (!cmd) return null;
  return (
    <div className="mt-1 flex items-center gap-2">
      <code className="min-w-0 flex-1 truncate rounded bg-foreground/5 px-2 py-1 text-xs">
        {cmd}
      </code>
      <Button
        size="sm"
        variant="ghost"
        onPress={() => {
          navigator.clipboard?.writeText(cmd).then(() => {
            setCopied(true);
            setTimeout(() => setCopied(false), 1500);
          });
        }}
      >
        {copied ? t('common.copied') : t('up.copyCmd')}
      </Button>
    </div>
  );
}

export default function Updates() {
  const t = useT();
  const { data, reload } = useApi<Payload>('/sources');
  const [checking, setChecking] = useState(false);
  const [checkErr, setCheckErr] = useState('');

  const recheck = async () => {
    setChecking(true);
    setCheckErr('');
    try {
      const res = await fetch('/api/v1/sources/check', { method: 'POST' });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      await reload();
    } catch (e) {
      // a silently swallowed failure here left the page claiming yesterday's
      // state was fresh — say what failed and that the shown data is old
      setCheckErr(t('up.checkFailed', { err: String(e) }));
    } finally {
      setChecking(false);
    }
  };

  if (!data) {
    return <div className="flex justify-center py-20"><Spinner aria-label={t('common.loading')} /></div>;
  }

  const behind = data.items.filter((i) => i.state === 'behind');
  const moved = data.items.filter((i) => i.state === 'moved');
  const rest = data.items.filter((i) => i.state !== 'behind' && i.state !== 'moved');

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-foreground/70">
          {t('up.traceable', {
            n: data.items.length,
            total: data.library_total,
            untraced: data.untraced,
          })}
        </span>
        <Button size="sm" className="ml-auto" isDisabled={checking} onPress={recheck}>
          {checking ? t('up.rechecking') : t('up.recheck')}
        </Button>
        {checkErr && (
          <span className="w-full text-right text-xs text-red-600 dark:text-red-400">{checkErr}</span>
        )}
      </div>

      <Card>
        <Card.Header className="pb-2">
          <div className="flex items-center gap-2">
            <Chip size="sm" className={STATE_CLASS.behind}>{updateLabel('behind')}</Chip>
            <Card.Title className="text-base">{t('up.behind.title')}</Card.Title>
            <span className="tabular-nums text-sm text-foreground/60">{behind.length}</span>
          </div>
          <Card.Description>
            {t('up.behind.desc', { cmd: 'git pull --ff-only' })}
          </Card.Description>
        </Card.Header>
        <Card.Content>
          {behind.length === 0 ? (
            <p className="text-sm text-foreground/60">{t('up.behind.none')}</p>
          ) : (
            <ul className="flex flex-col gap-3">
              {behind.map((i) => (
                <li key={i.skill_id} className="border-b border-foreground/5 pb-3 last:border-0">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="font-medium">{i.skill_id}</span>
                    <span className="font-mono text-xs text-foreground/60">
                      {i.local_ref} → {i.remote_ref}
                    </span>
                    <span className="text-xs text-foreground/60">
                      {t('up.checkedAt',
                        { when: fmtRel(new Date(i.checked_at * 1000).toISOString()) })}
                    </span>
                  </div>
                  <div className="mt-0.5 break-all text-xs text-foreground/60">{i.origin}</div>
                  <UpdateButton row={i} onDone={reload} />
                  <Cmd cmd={i.update_cmd} />
                </li>
              ))}
            </ul>
          )}
        </Card.Content>
      </Card>

      {moved.length > 0 && (
        <Card>
          <Card.Header className="pb-2">
            <div className="flex items-center gap-2">
              <Chip size="sm" className={STATE_CLASS.moved}>{updateLabel('moved')}</Chip>
              <Card.Title className="text-base">{t('up.moved.title')}</Card.Title>
              <span className="tabular-nums text-sm text-foreground/60">{moved.length}</span>
            </div>
            <Card.Description>{t('up.moved.desc')}</Card.Description>
          </Card.Header>
          <Card.Content>
            <ul className="flex flex-col gap-1.5">
              {moved.map((i) => (
                <li key={i.skill_id} className="flex flex-wrap items-baseline gap-2 text-sm">
                  <span>{i.skill_id}</span>
                  <a className="text-xs text-sky-600 underline dark:text-sky-400"
                     href={i.origin} target="_blank" rel="noreferrer">{i.origin}</a>
                </li>
              ))}
            </ul>
          </Card.Content>
        </Card>
      )}

      <Card>
        <Card.Header className="pb-2">
          <Card.Title className="text-base">{t('up.rest.title')}</Card.Title>
          <Card.Description>{t('up.rest.desc')}</Card.Description>
        </Card.Header>
        <Card.Content>
          <ul className="flex flex-col gap-1.5">
            {rest.map((i) => (
              <li key={i.skill_id} className="flex flex-wrap items-baseline gap-2 text-sm">
                <Chip size="sm" className={STATE_CLASS[i.state] ?? STATE_CLASS.unknown}>
                  {updateLabel(i.state) || i.state}
                </Chip>
                <span>{i.skill_id}</span>
                {i.local_ref && (
                  <span className="font-mono text-xs text-foreground/60">{i.local_ref}</span>
                )}
                {i.origin && (
                  <span className="truncate text-xs text-foreground/60">{i.origin}</span>
                )}
                {i.confidence === 'inferred' && (
                  <Chip size="sm" className="bg-foreground/10 text-foreground/60"
                        title={i.evidence}>{t('up.inferred')}</Chip>
                )}
                {i.error && (
                  <span className="text-xs text-red-600 dark:text-red-400">{i.error}</span>
                )}
              </li>
            ))}
          </ul>
        </Card.Content>
      </Card>
    </div>
  );
}
