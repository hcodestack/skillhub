import { useState } from 'react';
import { Chip } from '@heroui/react';
import { useT, type MsgKey } from './i18n';

/* The canonical explanation of every MCP endpoint state, in the same shape as
 * the link-state explainer, because it answers the same question: what is this
 * and do I need to do anything about it.
 *
 * The states exist because a skill served over MCP is not installed anywhere.
 * SEP-2640 requires hosts to cache served content outside every skill
 * discovery path, so there is nothing on disk for the scanner to find and the
 * only observable is the server itself. Two of these states are deliberate
 * refusals rather than failures, and saying so is most of the point. */

export type McpVerdict = 'ok' | 'attention' | 'info' | 'refused';

export const MCP_VERDICT_CLASS: Record<McpVerdict, string> = {
  ok: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  attention: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  info: 'bg-foreground/10 text-foreground/60',
  refused: 'bg-sky-500/15 text-sky-700 dark:text-sky-300',
};

export type McpState =
  | 'served' | 'empty' | 'no-extension' | 'auth' | 'unreachable' | 'declared' | '';

export const MCP_STATES: { key: Exclude<McpState, ''>; verdict: McpVerdict; color: string }[] = [
  { key: 'served', verdict: 'ok', color: 'var(--sh-link-ok)' },
  { key: 'empty', verdict: 'info', color: 'var(--sh-link-vendored)' },
  { key: 'no-extension', verdict: 'info', color: 'var(--sh-link-unrooted, #8a8a90)' },
  { key: 'auth', verdict: 'refused', color: '#2a78d6' },
  { key: 'declared', verdict: 'refused', color: '#2a78d6' },
  { key: 'unreachable', verdict: 'attention', color: '#ec835a' },
];

export function mcpStateMeta(state: string) {
  return MCP_STATES.find((s) => s.key === state);
}

export function McpStateChip({ state }: { state: string }) {
  const t = useT();
  const meta = mcpStateMeta(state);
  if (!meta) return null;
  return (
    <Chip size="sm" className={MCP_VERDICT_CLASS[meta.verdict]}>
      {t(`mcp.state.${meta.key}` as MsgKey)}
    </Chip>
  );
}

export function McpDocPanel() {
  const t = useT();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {MCP_STATES.map((s) => (
        <div key={s.key} className="rounded-lg border border-foreground/10 p-3">
          <div className="mb-1 flex items-center gap-2">
            <span className="h-2.5 w-5 shrink-0 rounded-sm" style={{ background: s.color }} />
            <span className="text-sm font-medium">{t(`mcp.state.${s.key}` as MsgKey)}</span>
            <Chip size="sm" className={MCP_VERDICT_CLASS[s.verdict]}>
              {t(`mcp.verdict.${s.verdict}` as MsgKey)}
            </Chip>
          </div>
          <p className="text-xs leading-relaxed text-foreground/75">
            {t(`mcp.state.${s.key}.what` as MsgKey)}
          </p>
        </div>
      ))}
    </div>
  );
}

export function McpDocToggle() {
  const [open, setOpen] = useState(false);
  const t = useT();
  return (
    <>
      <button
        type="button"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className="rounded-md border border-foreground/15 px-2 py-0.5 text-xs text-foreground/70 transition-colors hover:border-foreground/30 hover:text-foreground"
      >
        {open ? t('link.explain.close') : t('link.explain.open')}
      </button>
      {open && (
        <div className="w-full basis-full pt-1">
          <McpDocPanel />
        </div>
      )}
    </>
  );
}
