import { useState } from 'react';
import { Button, Card, Chip, Spinner } from '@heroui/react';
import { fmtRel, useApi, UPDATE_LABEL, type SourceRow } from '../lib/api';

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
        setMsg(d.changed ? `已更新 ${d.from} → ${d.to}${d.note ? '。' + d.note : ''}` : '已是最新');
        onDone();
      } else {
        setMsg(`未更新：${d.error}`);
      }
    } catch (e) {
      setMsg(`请求失败：${String(e)}`);
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="mt-1.5">
      <Button size="sm" isDisabled={busy} onPress={run}>
        {busy ? '更新中…' : '一键更新'}
      </Button>
      {msg && <span className="ml-2 text-xs text-foreground/70">{msg}</span>}
    </div>
  );
}

function Cmd({ cmd }: { cmd: string }) {
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
        {copied ? '已复制' : '复制命令'}
      </Button>
    </div>
  );
}

export default function Updates() {
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
      setCheckErr(`检查失败（${String(e)}）；下方仍为上次结果`);
    } finally {
      setChecking(false);
    }
  };

  if (!data) {
    return <div className="flex justify-center py-20"><Spinner aria-label="加载中" /></div>;
  }

  const behind = data.items.filter((i) => i.state === 'behind');
  const moved = data.items.filter((i) => i.state === 'moved');
  const rest = data.items.filter((i) => i.state !== 'behind' && i.state !== 'moved');

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-sm text-foreground/70">
          可追溯上游 <b>{data.items.length}</b> / 库内 {data.library_total}
          （<b>{data.untraced}</b> 个来源未记录，无法检查更新）
        </span>
        <Button size="sm" className="ml-auto" isDisabled={checking} onPress={recheck}>
          {checking ? '检查中…' : '重新检查上游'}
        </Button>
        {checkErr && (
          <span className="w-full text-right text-xs text-red-600 dark:text-red-400">{checkErr}</span>
        )}
      </div>

      <Card>
        <Card.Header className="pb-2">
          <div className="flex items-center gap-2">
            <Chip size="sm" className={STATE_CLASS.behind}>有更新</Chip>
            <Card.Title className="text-base">上游已更新的技能</Card.Title>
            <span className="tabular-nums text-sm text-foreground/60">{behind.length}</span>
          </div>
          <Card.Description>
            库内版本落后于上游仓库。「一键更新」执行 <code>git pull --ff-only</code>：
            只改库内真源、不动任何软链入口；工作区若有未提交改动会被拒绝，不覆盖你的修改。
          </Card.Description>
        </Card.Header>
        <Card.Content>
          {behind.length === 0 ? (
            <p className="text-sm text-foreground/60">全部为最新。</p>
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
                      检查于 {fmtRel(new Date(i.checked_at * 1000).toISOString())}
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
              <Chip size="sm" className={STATE_CLASS.moved}>上游有新提交</Chip>
              <Card.Title className="text-base">上游仓库自记录以来已更新</Card.Title>
              <span className="tabular-nums text-sm text-foreground/60">{moved.length}</span>
            </div>
            <Card.Description>
              这些技能是从上游仓库复制进库的，本地没有自己的版本号，只能判断上游是否有了新提交
              —— 是否需要同步要你自行判断。
            </Card.Description>
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
          <Card.Title className="text-base">其余可追溯技能</Card.Title>
          <Card.Description>
            安装器管理的技能由其自身更新器负责（例如 lark-cli update）。
          </Card.Description>
        </Card.Header>
        <Card.Content>
          <ul className="flex flex-col gap-1.5">
            {rest.map((i) => (
              <li key={i.skill_id} className="flex flex-wrap items-baseline gap-2 text-sm">
                <Chip size="sm" className={STATE_CLASS[i.state] ?? STATE_CLASS.unknown}>
                  {UPDATE_LABEL[i.state] ?? i.state}
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
                        title={i.evidence}>来源为推断</Chip>
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
