import { Card, Chip } from '@heroui/react';
import { fmtRel, sourceLabel, type SkillItem } from '../lib/api';
import { categoryLabel, useT } from '../lib/i18n';
import { AgentChips } from './AgentChips';

/* The card view shows exactly what a table row shows — no new facts, no
 * actions — arranged so a description can breathe. Tables win for comparing
 * numbers down a column; cards win for reading what a skill *is*. Both exist
 * because the overview is used both ways. (Pattern from skills-hub's My
 * Skills page, minus everything that writes.) */
export function SkillCard({ item, onOpen }: { item: SkillItem; onOpen: () => void }) {
  const t = useT();
  const high = item.vetting?.top_severity === 'high';
  const behind = item.update?.state === 'behind';
  return (
    <Card className="flex h-full flex-col transition-colors hover:border-foreground/25">
      <button type="button" onClick={onOpen}
              className="flex h-full flex-col text-left focus-visible:outline-2 focus-visible:outline-offset-2">
        <Card.Content className="flex flex-1 flex-col gap-2 px-4 py-3">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="truncate font-medium">{item.name}</span>
                {!item.in_library && (
                  <Chip size="sm" className="shrink-0 bg-foreground/10 text-foreground/60">
                    {t(item.source === 'unmanaged' ? 'ov.chip.unmanaged' : 'ov.chip.external')}
                  </Chip>
                )}
              </div>
              {item.id && item.id !== item.name && (
                <div className="truncate font-mono text-xs text-foreground/60">{item.id}</div>
              )}
            </div>
            <div className="flex shrink-0 gap-1">
              {high && (
                <Chip size="sm" className="bg-red-500/15 text-red-700 dark:text-red-300">
                  {t('ov.chip.high')}
                </Chip>
              )}
              {behind && (
                <Chip size="sm" className="bg-amber-500/15 text-amber-700 dark:text-amber-300">
                  {t('ov.chip.update')}
                </Chip>
              )}
            </div>
          </div>

          <p className="line-clamp-2 text-sm leading-relaxed text-foreground/70">
            {item.description || t('dr.noDescription')}
          </p>

          <div className="flex flex-wrap items-center gap-1">
            <span className="mr-1 text-xs text-foreground/60">{sourceLabel(item.source)}</span>
            {item.tags.map((tag) => (
              <span key={tag} className="rounded bg-sky-500/10 px-1 text-[11px] text-sky-700 dark:text-sky-300">
                {categoryLabel(tag)}
              </span>
            ))}
          </div>

          <div className="mt-auto flex flex-wrap items-center justify-between gap-2 border-t border-foreground/10 pt-2">
            <AgentChips agents={item.agents} usage={item.agent_usage} />
            {/* label before number: "Loads 1" needs no plural, "1 loads" does */}
            <dl className="flex gap-3 text-xs text-foreground/60">
              <div className="flex gap-1"><dt>{t('ov.col.installs')}</dt>
                <dd className="tabular-nums font-medium text-foreground/80">{item.installs.length || '—'}</dd></div>
              <div className="flex gap-1"><dt>{t('ov.col.usage')}</dt>
                <dd className="tabular-nums font-medium text-foreground/80">{item.usage.total || '—'}</dd></div>
              <div className="flex gap-1"><dt className="sr-only">{t('ov.col.last')}</dt>
                <dd>{fmtRel(item.usage.last)}</dd></div>
            </dl>
          </div>
        </Card.Content>
      </button>
    </Card>
  );
}
