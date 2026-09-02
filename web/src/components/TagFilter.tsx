import { useMemo, useState } from 'react';
import { Label, ListBox, Popover, SearchField } from '@heroui/react';
import { categoryLabel, useT } from '../lib/i18n';

export const UNTAGGED = '__untagged';

/* Multi-select over domain tags, match-any. The overview already prints a
 * skill's tags on every row; until now there was no way to filter by them.
 * Counts come from the whole list, not the current result, so a tag's number
 * means "how many skills carry this" and does not jump as you type. Modelled
 * on skills-hub's tag menu (search, counts, an explicit "untagged" row). */
export function TagFilter({ counts, untagged, selected, onChange }: {
  counts: Map<string, number>;   // tag key -> skills carrying it
  untagged: number;              // skills with no tag at all
  selected: Set<string>;         // tag keys, may include UNTAGGED
  onChange: (next: Set<string>) => void;
}) {
  const t = useT();
  const [q, setQ] = useState('');
  const tags = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return [...counts.entries()]
      .map(([key, n]) => ({ key, n, label: categoryLabel(key) }))
      .filter((x) => !needle || x.label.toLowerCase().includes(needle) || x.key.includes(needle))
      .sort((a, b) => b.n - a.n || a.label.localeCompare(b.label));
  }, [counts, q]);
  const n = selected.size;
  const active = n > 0;

  return (
    <Popover>
      <Popover.Trigger
        className={`inline-flex h-9 cursor-pointer items-center gap-1.5 rounded-lg border px-3 text-sm transition-colors ${
          active
            ? 'border-accent/40 bg-accent/10 text-accent'
            : 'border-foreground/15 bg-background text-foreground hover:border-foreground/30'
        }`}
      >
        <span>{active ? t('ov.filter.tags.n', { n }) : t('ov.filter.tags')}</span>
        <svg viewBox="0 0 16 16" width={12} height={12} aria-hidden className="fill-none stroke-current" strokeWidth={1.6}>
          <path d="M4 6l4 4 4-4" />
        </svg>
      </Popover.Trigger>
      <Popover.Content placement="bottom start" className="w-72">
        <Popover.Dialog aria-label={t('ov.tags.title')} className="flex flex-col gap-2 p-2">
          <div className="flex items-center justify-between px-1 text-xs text-foreground/60">
            <span className="font-medium text-foreground/80">{t('ov.tags.title')}</span>
            <span>{t('ov.tags.matchAny')}</span>
          </div>
          <SearchField aria-label={t('ov.tags.search')} value={q} onChange={setQ} className="w-full">
            <SearchField.Group>
              <SearchField.SearchIcon />
              <SearchField.Input placeholder={t('ov.tags.search')} />
              <SearchField.ClearButton />
            </SearchField.Group>
          </SearchField>
          <ListBox
            aria-label={t('ov.tags.title')}
            selectionMode="multiple"
            selectedKeys={selected}
            onSelectionChange={(keys) => {
              if (keys === 'all') return;
              onChange(new Set([...keys].map(String)));
            }}
            className="max-h-72 overflow-y-auto"
          >
            {(!q || t('ov.tags.untagged').toLowerCase().includes(q.trim().toLowerCase())) && (
              <ListBox.Item id={UNTAGGED} textValue={t('ov.tags.untagged')}>
                <Label className="flex-1 text-foreground/70">{t('ov.tags.untagged')}</Label>
                <span className="tabular-nums text-xs text-foreground/50">{untagged}</span>
                <ListBox.ItemIndicator />
              </ListBox.Item>
            )}
            {tags.map((x) => (
              <ListBox.Item key={x.key} id={x.key} textValue={x.label}>
                <Label className="flex-1">{x.label}</Label>
                <span className="tabular-nums text-xs text-foreground/50">{x.n}</span>
                <ListBox.ItemIndicator />
              </ListBox.Item>
            ))}
          </ListBox>
          <div className="flex justify-end px-1">
            <button type="button" disabled={!active}
                    onClick={() => onChange(new Set())}
                    className="text-xs text-foreground/60 hover:text-foreground disabled:opacity-40">
              {t('ov.tags.clear')}
            </button>
          </div>
        </Popover.Dialog>
      </Popover.Content>
    </Popover>
  );
}
