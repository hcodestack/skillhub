import { useState } from 'react';
import { Chip } from '@heroui/react';
import { useT, type MsgKey } from './i18n';

/* The canonical explanation of every link state the dashboard reports.
 *
 * These four words (symlink / repo-vendored / stray copy / broken link) appear
 * on three pages, and their meaning used to live only in hover tooltips —
 * invisible on touch, undiscoverable by mouse, and silent on the question
 * people actually have: "do I need to do anything about this?" (Nielsen #10:
 * help in context.)
 *
 * One source of truth here; the topology legend and any future page render it.
 * Wording lives in lib/i18n.tsx under `link.<key>.*`, so both languages stay
 * one edit apart. The dashboard stays read-only — every action below is a
 * command for the user to run, per the management policy this project observes. */

export type LinkVerdict = 'ok' | 'attention' | 'fix' | 'env';

export const VERDICT_CLASS: Record<LinkVerdict, string> = {
  ok: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300',
  attention: 'bg-amber-500/15 text-amber-700 dark:text-amber-300',
  fix: 'bg-red-500/15 text-red-700 dark:text-red-300',
  env: 'bg-foreground/10 text-foreground/60',
};

export type LinkDoc = { key: string; color: string; verdict: LinkVerdict };

export const LINK_DOC: LinkDoc[] = [
  { key: 'symlink', color: 'var(--sh-link-ok)', verdict: 'ok' },
  { key: 'vendored', color: 'var(--sh-link-vendored)', verdict: 'ok' },
  { key: 'entity', color: '#ec835a', verdict: 'attention' },
  { key: 'broken', color: '#d03b3b', verdict: 'fix' },
  { key: 'unrooted', color: 'var(--sh-link-unrooted, #8a8a90)', verdict: 'env' },
];

/** Expandable explainer: a toggle where the legend lives, so the answer sits
 * next to the question instead of in a hover tooltip nobody finds. */
export function LinkDocPanel({ show = LINK_DOC.map((d) => d.key) }: { show?: string[] }) {
  const t = useT();
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {LINK_DOC.filter((d) => show.includes(d.key)).map((d) => (
        <div key={d.key} className="rounded-lg border border-foreground/10 p-3">
          <div className="mb-1 flex items-center gap-2">
            <span className="h-2.5 w-5 shrink-0 rounded-sm" style={{ background: d.color }} />
            <span className="text-sm font-medium">{t(`link.${d.key}` as MsgKey)}</span>
            <Chip size="sm" className={VERDICT_CLASS[d.verdict]}>
              {t(`verdict.${d.verdict}` as MsgKey)}
            </Chip>
          </div>
          <p className="text-xs leading-relaxed text-foreground/75">
            {t(`link.${d.key}.what` as MsgKey)}
          </p>
          <p className="mt-1.5 text-xs leading-relaxed">
            <span className="font-medium">{t('link.action.prefix')}</span>
            <span className="text-foreground/75">{t(`link.${d.key}.action` as MsgKey)}</span>
          </p>
        </div>
      ))}
    </div>
  );
}

export function LinkDocToggle() {
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
          <LinkDocPanel />
        </div>
      )}
    </>
  );
}
