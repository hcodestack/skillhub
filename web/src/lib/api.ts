import { useCallback, useEffect, useState } from 'react';

export type Install = {
  host: string; agent: string; scope: string; project_path: string;
  entry_name: string; entry_path: string; link_type: string;
  target_path: string; last_seen: string;
  shared_with: string; content_hash: string; vcs: string;
};

export type Usage = { total: number; d7: number; d30: number; last: string | null };

export type UpdateInfo = {
  kind: string; origin: string; state: string;
  local_ref: string; remote_ref: string; checked_at: number;
  error: string; update_cmd: string;
  confidence: string; subpath: string; evidence: string;
};

export type VettingFinding = {
  rule: string; category: string; severity: string;
  description: string; file: string; line: number; excerpt: string;
};
export type Vetting = {
  count: number; top_severity: string; findings: VettingFinding[];
  scanned_at: number;
};

export type SkillItem = {
  key: string; id: string | null; name: string; description: string;
  source: string; category: string; tags: string[]; in_library: boolean;
  agents: string[]; installs: Install[]; usage: Usage;
  agent_usage: Record<string, number>;
  update: UpdateInfo | null;   // null = 上游来源未知，无法检查
  library_path: string;
  body_lines?: number;
  desc_chars?: number;
  vetting: Vetting | null;   // null = 无命中或尚未扫描
};

export type SourceRow = UpdateInfo & { skill_id: string; name: string };

export const UPDATE_LABEL: Record<string, string> = {
  behind: '有更新',
  current: '最新',
  moved: '上游有新提交',
  tracked: '已记录上游',
  installer: '安装器管理',
  error: '检查失败',
  unknown: '未知',
};

export type Tiles = {
  library_total: number; loaded_skills: number; events_total: number;
  events_d7: number; loose_entries: number; vendored_entries: number; broken_links: number;
  tools: number; hosts: number; metadata_tokens: number; library_root: string;
};

export type UsageEvent = {
  host: string; agent: string; skill_key: string; project: string;
  session_id: string; ts: string; source: string;
};

export type HealthSection = {
  key: string; severity: 'error' | 'warn' | 'info'; title: string;
  hint: string; count: number; items: Record<string, unknown>[];
};

export type HostRow = {
  id: string; os: string; last_report_at: string;
  agents: { agent: string; entries: number; global_entries: number; project_entries: number }[];
  events_total: number; last_event_ts: string | null;
};

const BASE = '/api/v1';

// Module-level GET cache (stale-while-revalidate). Switching tabs used to
// unmount every module, throw the data away and greet the user with a full-page
// spinner on each visit — the most-repeated interaction in the app paying the
// highest cost (Nielsen #1/#7; see docs/UX-AUDIT-20260901.md). With the cache,
// a revisited tab renders instantly from the last response while a background
// refetch keeps it current. Bonus: 总览 and 拓扑 both read /skills (~640 KB) —
// now it downloads once, not once per tab visit.
const cache = new Map<string, unknown>();
const inflight = new Map<string, Promise<unknown>>();

export async function api<T>(path: string, opts?: { fresh?: boolean }): Promise<T> {
  if (!opts?.fresh) {
    if (cache.has(path)) return cache.get(path) as T;
    const running = inflight.get(path);
    if (running) return running as Promise<T>;
  }
  const p = fetch(BASE + path)
    .then((res) => {
      if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
      return res.json() as Promise<T>;
    })
    .then((d) => { cache.set(path, d); inflight.delete(path); return d; })
    .catch((e) => { inflight.delete(path); throw e; });
  inflight.set(path, p);
  return p;
}

/** Cached GET as a hook: instant data on revisit, background revalidate,
 * spinner only on the true first load. `reload()` bypasses the cache — use it
 * after an action that changes server state (e.g. 一键更新). */
export function useApi<T>(path: string) {
  const [data, setData] = useState<T | null>(() => (cache.get(path) as T) ?? null);
  const [error, setError] = useState('');
  useEffect(() => {
    let on = true;
    const had = cache.has(path);
    setData(had ? (cache.get(path) as T) : null);
    setError('');
    api<T>(path, { fresh: had })
      .then((d) => { if (on) setData(d); })
      .catch((e) => { if (on) setError(String(e)); });
    return () => { on = false; };
  }, [path]);
  const reload = useCallback(
    () => api<T>(path, { fresh: true }).then(setData).catch((e) => setError(String(e))),
    [path],
  );
  return { data, error, reload };
}

// Display names for every tool the reporter can scan (mirrors
// reporter/adapters/tool_table.py). A `shared:<dir>` key means one directory
// serves several tools, so it is labelled by the directory itself.
export const AGENT_LABEL: Record<string, string> = {
  'cursor': 'Cursor',
  'claude-code': 'Claude Code',
  'codex': 'Codex',
  'deepseek-harness': 'DeepSeek Harness',
  'opencode': 'OpenCode',
  'antigravity': 'Antigravity',
  'amp': 'Amp',
  'kimi-cli': 'Kimi Code CLI',
  'augment': 'Augment',
  'openclaw': 'OpenClaw',
  'copaw': 'Copaw',
  'cline': 'Cline',
  'codebuddy': 'CodeBuddy',
  'codewhale': 'CodeWhale',
  'workbuddy': 'WorkBuddy',
  'command-code': 'Command Code',
  'continue': 'Continue',
  'crush': 'Crush',
  'junie': 'Junie',
  'iflow-cli': 'iFlow CLI',
  'kiro-cli': 'Kiro CLI',
  'kode': 'Kode',
  'mcpjam': 'MCPJam',
  'mistral-vibe': 'Mistral Vibe',
  'mux': 'Mux',
  'openclaude': 'OpenClaude IDE',
  'openhands': 'OpenHands',
  'pi': 'Pi',
  'qoder': 'Qoder',
  'qoderwork': 'QoderWork',
  'qwen-code': 'Qwen Code',
  'trae': 'Trae',
  'trae-cn': 'Trae CN',
  'zencoder': 'Zencoder',
  'neovate': 'Neovate',
  'pochi': 'Pochi',
  'adal': 'AdaL',
  'kilo-code': 'Kilo Code',
  'roo-code': 'Roo Code',
  'goose': 'Goose',
  'gemini-cli': 'Gemini CLI',
  'github-copilot': 'GitHub Copilot',
  'clawdbot': 'Clawdbot',
  'droid': 'Droid',
  'windsurf': 'Windsurf',
  'moltbot': 'MoltBot',
  'hermes-agent': 'Hermes Agent'
};

export function agentLabel(agent: string): string {
  if (agent.startsWith('shared:')) return agent.slice(7);
  return AGENT_LABEL[agent] ?? agent;
}

export function isSharedDir(agent: string): boolean {
  return agent.startsWith('shared:');
}

export const SOURCE_LABEL: Record<string, string> = {
  organized: '第三方库',
  'self-made': '自制库',
  installer: '安装器',
  unmanaged: '未纳管',
  unresolved: '外部/插件',
};

export function fmtRel(ts: string | null | undefined): string {
  if (!ts) return '—';
  const t = new Date(ts).getTime();
  if (Number.isNaN(t)) return ts;
  const d = Date.now() - t;
  const day = 86400000;
  if (d < 3600000) return `${Math.max(1, Math.round(d / 60000))} 分钟前`;
  if (d < day) return `${Math.round(d / 3600000)} 小时前`;
  if (d < day * 30) return `${Math.round(d / day)} 天前`;
  return ts.slice(0, 10);
}
