import { useCallback, useEffect, useRef, useState } from 'react';
import { getLang, t, useLang, type MsgKey } from './i18n';

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
  update: UpdateInfo | null;   // null = upstream unknown, cannot be checked
  library_path: string;
  body_lines?: number;
  desc_chars?: number;
  vetting: Vetting | null;   // null = clean, or not scanned yet
};

export type SourceRow = UpdateInfo & { skill_id: string; name: string };

const UPDATE_STATES = ['behind', 'current', 'moved', 'tracked',
  'installer', 'error', 'unknown'];

/** Display name for an upstream state; '' for a state we have no wording for
 * (callers decide whether to fall back to the raw value or draw nothing). */
export function updateLabel(state: string): string {
  return UPDATE_STATES.includes(state) ? t(`update.${state}` as MsgKey) : '';
}

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
// refetch keeps it current. Bonus: the overview and the topology both read
// /skills (~640 KB) — now it downloads once, not once per tab visit.
const cache = new Map<string, unknown>();
const inflight = new Map<string, Promise<unknown>>();

/** Some responses carry prose the server localises (health section titles, the
 * governance report), so the language is part of the request — and therefore
 * part of the cache key, or a switch would serve the old language from cache. */
function url(path: string): string {
  return BASE + path + (path.includes('?') ? '&' : '?') + 'lang=' + getLang();
}

export async function api<T>(path: string, opts?: { fresh?: boolean }): Promise<T> {
  const u = url(path);
  if (!opts?.fresh) {
    if (cache.has(u)) return cache.get(u) as T;
    const running = inflight.get(u);
    if (running) return running as Promise<T>;
  }
  const p = fetch(u)
    .then((res) => {
      if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
      return res.json() as Promise<T>;
    })
    .then((d) => { cache.set(u, d); inflight.delete(u); return d; })
    .catch((e) => { inflight.delete(u); throw e; });
  inflight.set(u, p);
  return p;
}

/** Cached GET as a hook: instant data on revisit, background revalidate,
 * spinner only on the true first load. `reload()` bypasses the cache — use it
 * after an action that changes server state (e.g. the one-click update). */
export function useApi<T>(path: string) {
  const lang = useLang();
  const [data, setData] = useState<T | null>(() => (cache.get(url(path)) as T) ?? null);
  const [error, setError] = useState('');
  const lastPath = useRef(path);
  useEffect(() => {
    let on = true;
    const u = url(path);
    const had = cache.has(u);
    const samePath = lastPath.current === path;
    lastPath.current = path;
    // A language switch changes the URL but not the data behind it — same rows,
    // same numbers, different wording. Blanking the page to a spinner while the
    // other language loads would undo exactly what the cache above is for
    // (the health page takes seconds to rebuild), so the current view stays up
    // and is replaced when the translated response lands.
    setData((prev) => (had ? (cache.get(u) as T) : (samePath ? prev : null)));
    setError('');
    api<T>(path, { fresh: had })
      .then((d) => { if (on) setData(d); })
      .catch((e) => { if (on) setError(String(e)); });
    return () => { on = false; };
  }, [path, lang]);
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

const SOURCES = ['organized', 'self-made', 'installer', 'unmanaged', 'unresolved'];

export function sourceLabel(source: string): string {
  return SOURCES.includes(source) ? t(`source.${source}` as MsgKey) : source;
}

export function fmtRel(ts: string | null | undefined): string {
  if (!ts) return '—';
  const at = new Date(ts).getTime();
  if (Number.isNaN(at)) return ts;
  const d = Date.now() - at;
  const day = 86400000;
  if (d < 3600000) return t('rel.minutes', { n: Math.max(1, Math.round(d / 60000)) });
  if (d < day) return t('rel.hours', { n: Math.round(d / 3600000) });
  if (d < day * 30) return t('rel.days', { n: Math.round(d / day) });
  return ts.slice(0, 10);
}
