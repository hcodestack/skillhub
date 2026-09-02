import { Chip } from '@heroui/react';
import { agentLabel, isSharedDir } from '../lib/api';
import { t } from '../lib/i18n';
import { ToolIcon } from './ToolIcon';

// The three agents with usage tracking keep their established colors; the rest
// get a stable hue from the key so 40+ tools stay distinguishable without a
// hand-maintained palette.
const FIXED: Record<string, string> = {
  'claude-code': 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-300',
  codex: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-300',
  workbuddy: 'bg-amber-500/15 text-amber-600 dark:text-amber-300',
};

const HUES = [
  'bg-sky-500/15 text-sky-700 dark:text-sky-300',
  'bg-rose-500/15 text-rose-700 dark:text-rose-300',
  'bg-teal-500/15 text-teal-700 dark:text-teal-300',
  'bg-violet-500/15 text-violet-700 dark:text-violet-300',
  'bg-orange-500/15 text-orange-700 dark:text-orange-300',
  'bg-cyan-500/15 text-cyan-700 dark:text-cyan-300',
  'bg-fuchsia-500/15 text-fuchsia-700 dark:text-fuchsia-300',
  'bg-lime-600/15 text-lime-700 dark:text-lime-300',
];

function agentClass(agent: string): string {
  if (FIXED[agent]) return FIXED[agent];
  if (isSharedDir(agent)) return 'bg-foreground/10 text-foreground/70';
  let h = 0;
  for (let i = 0; i < agent.length; i++) h = (h * 31 + agent.charCodeAt(i)) >>> 0;
  return HUES[h % HUES.length];
}

export function AgentChip({ agent, count, title }: { agent: string; count?: number; title?: string }) {
  return (
    <Chip size="sm" className={`${agentClass(agent)} gap-1`} title={title}>
      <ToolIcon agent={agent} size={12} />
      {isSharedDir(agent) ? t('agent.shared') : ''}
      {agentLabel(agent)}
      {count != null && count > 0 ? ` ×${count}` : ''}
    </Chip>
  );
}

export function AgentChips({ agents, usage }: { agents: string[]; usage?: Record<string, number> }) {
  if (!agents.length) return <span className="text-foreground/40">—</span>;
  const shown = agents.slice(0, 4);
  return (
    <div className="flex flex-wrap gap-1">
      {shown.map((a) => (
        <AgentChip key={a} agent={a} count={usage?.[a]} />
      ))}
      {agents.length > shown.length && (
        <Chip size="sm" className="bg-foreground/10 text-foreground/60"
          title={agents.slice(4).map(agentLabel).join(', ')}>
          +{agents.length - shown.length}
        </Chip>
      )}
    </div>
  );
}
