import { useMemo, useState } from 'react';
import {
  Card, Chip, Label, ListBox, SearchField, Select, Spinner, Table,
} from '@heroui/react';
import {
  agentLabel, fmtRel, sourceLabel, useApi, type SkillItem, type Tiles,
} from '../lib/api';
import { AgentChips } from '../components/AgentChips';
import { prettyPath } from '../lib/paths';
import { SkillDrawer } from '../components/SkillDrawer';
import { categoryLabel, useT, vendorLabel } from '../lib/i18n';

type SortDesc = { column: string | number; direction: 'ascending' | 'descending' };

// One metric per tile ("106 / 137" was two metrics sharing a tile and wrapped
// onto two lines), and a tile that names a problem is a door to it (Shneiderman:
// overview first, details on demand) — `href` deep-links into the tab/section
// that explains the number. `tone` separates "go look now" (red, matches the
// health page's error severity) from "worth attention" (amber).
function Tile({ label, value, tone, href, title }: {
  label: string; value: number | string;
  tone?: 'warn' | 'error'; href?: string; title?: string;
}) {
  const color = tone === 'error' ? 'text-red-600 dark:text-red-400'
    : tone === 'warn' ? 'text-amber-600 dark:text-amber-400' : '';
  const body = (
    <Card.Content className="px-4 py-3">
      <div className={`text-2xl font-semibold tabular-nums ${color}`}>{value}</div>
      <div className="mt-0.5 whitespace-nowrap text-xs text-foreground/60">{label}</div>
    </Card.Content>
  );
  if (!href) {
    return <Card className="min-w-28 flex-1" title={title}>{body}</Card>;
  }
  return (
    <Card className="min-w-28 flex-1 transition-colors hover:border-foreground/25" title={title}>
      <a href={href} className="block focus-visible:outline-2 focus-visible:outline-offset-2">
        {body}
      </a>
    </Card>
  );
}

function Filter({ label, value, onChange, options, width = 'w-40' }: {
  label: string; value: string; onChange: (v: string) => void;
  options: { id: string; label: string }[]; width?: string;
}) {
  return (
    <Select
      aria-label={label}
      selectedKey={value}
      onSelectionChange={(k) => onChange(String(k))}
      className={width}
    >
      <Select.Trigger>
        <Select.Value />
        <Select.Indicator />
      </Select.Trigger>
      <Select.Popover>
        <ListBox>
          {options.map((o) => (
            <ListBox.Item key={o.id} id={o.id} textValue={o.label}>
              <Label>{o.label}</Label>
              <ListBox.ItemIndicator />
            </ListBox.Item>
          ))}
        </ListBox>
      </Select.Popover>
    </Select>
  );
}

export default function Overview() {
  const t = useT();
  const { data: tiles } = useApi<Tiles>('/stats/tiles');
  const { data: skills } = useApi<{ items: SkillItem[] }>('/skills');
  const items = skills?.items ?? [];
  const loading = !tiles && !skills;
  const [q, setQ] = useState('');
  const [source, setSource] = useState('all');
  const [agent, setAgent] = useState('all');
  const [category, setCategory] = useState('all');
  const [loadedOnly, setLoadedOnly] = useState('all');
  const [sort, setSort] = useState<SortDesc>({ column: 'total', direction: 'descending' });
  const [sel, setSel] = useState<SkillItem | null>(null);

  const agentOptions = useMemo(() => {
    const set = new Map<string, number>();
    for (const it of items) for (const a of it.agents) set.set(a, (set.get(a) ?? 0) + 1);
    return [...set.entries()].sort((a, b) => b[1] - a[1]);
  }, [items]);

  const categories = useMemo(() => {
    const set = new Map<string, number>();
    for (const it of items) {
      const c = it.category || 'uncategorized';
      set.set(c, (set.get(c) ?? 0) + 1);
    }
    return [...set.entries()].sort((a, b) => b[1] - a[1]);
  }, [items]);

  const filtered = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return items.filter((it) => {
      if (source !== 'all' && it.source !== source) return false;
      if (agent !== 'all' && !it.agents.includes(agent)) return false;
      if (category !== 'all' && (it.category || 'uncategorized') !== category) return false;
      if (loadedOnly === 'loaded' && it.installs.length === 0) return false;
      if (loadedOnly === 'used' && it.usage.total === 0) return false;
      if (loadedOnly === 'unused' && it.usage.total > 0) return false;
      if (loadedOnly === 'behind' && it.update?.state !== 'behind') return false;
      if (loadedOnly === 'risky' && it.vetting?.top_severity !== 'high') return false;
      if (needle) {
        const hay = `${it.key} ${it.name} ${it.description} ${it.tags.join(' ')}`.toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
  }, [items, q, source, agent, category, loadedOnly]);

  const sorted = useMemo(() => {
    const dir = sort.direction === 'ascending' ? 1 : -1;
    const val = (it: SkillItem): string | number => {
      switch (sort.column) {
        case 'name': return it.name.toLowerCase();
        case 'installs': return it.installs.length;
        case 'total': return it.usage.total;
        case 'd7': return it.usage.d7;
        case 'last': return it.usage.last ?? '';
        default: return 0;
      }
    };
    return [...filtered].sort((a, b) => {
      const va = val(a); const vb = val(b);
      if (va < vb) return -1 * dir;
      if (va > vb) return 1 * dir;
      return a.name.localeCompare(b.name);
    });
  }, [filtered, sort]);

  if (loading) {
    return <div className="flex justify-center py-20"><Spinner aria-label={t('common.loading')} /></div>;
  }

  return (
    <div className="flex flex-col gap-5">
      {tiles && (
        <div className="flex flex-wrap gap-3">
          <Tile label={t('ov.tile.library')} value={tiles.library_total} />
          <Tile label={t('ov.tile.loaded')} value={tiles.loaded_skills} href="#topology" />
          <Tile label={t('ov.tile.events')} value={tiles.events_total} />
          <Tile label={t('ov.tile.events7')} value={tiles.events_d7} />
          <Tile label={t('ov.tile.loose')} value={tiles.loose_entries}
                tone={tiles.loose_entries > 0 ? 'warn' : undefined}
                href="#health/loose_entities"
                title={t('ov.tile.loose.title')} />
          <Tile label={t('ov.tile.broken')} value={tiles.broken_links}
                tone={tiles.broken_links > 0 ? 'error' : undefined}
                href="#health/broken_links"
                title={t('ov.tile.broken.title')} />
          <Tile label={t('ov.tile.tools')} value={tiles.tools} href="#hosts" />
          <Tile label={t('ov.tile.hosts')} value={tiles.hosts} href="#hosts" />
          <Tile label={t('ov.tile.tokens')} value={`~${(tiles.metadata_tokens / 1000).toFixed(1)}k`}
                title={t('ov.tile.tokens.title')} />
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <SearchField
          aria-label={t('ov.search')}
          value={q}
          onChange={setQ}
          className="w-64"
        >
          <SearchField.Group>
            <SearchField.SearchIcon />
            <SearchField.Input placeholder={t('ov.search.placeholder')} />
            <SearchField.ClearButton />
          </SearchField.Group>
        </SearchField>
        <Filter label={t('ov.filter.source')} value={source} onChange={setSource} options={[
          { id: 'all', label: t('ov.filter.source.all') },
          { id: 'organized', label: sourceLabel('organized') },
          { id: 'self-made', label: sourceLabel('self-made') },
          { id: 'installer', label: sourceLabel('installer') },
          { id: 'unmanaged', label: sourceLabel('unmanaged') },
          { id: 'unresolved', label: sourceLabel('unresolved') },
        ]} />
        <Filter label={t('ov.filter.tool')} value={agent} onChange={setAgent} width="w-48" options={[
          { id: 'all', label: t('ov.filter.tool.all') },
          ...agentOptions.map(([a, n]) => ({ id: a, label: `${agentLabel(a)} (${n})` })),
        ]} />
        <Filter label={t('ov.filter.category')} value={category} onChange={setCategory} width="w-44" options={[
          { id: 'all', label: t('ov.filter.category.all') },
          ...categories.map(([c, n]) => ({
            id: c,
            label: `${c === 'uncategorized' ? t('common.uncategorized') : vendorLabel(c)} (${n})`,
          })),
        ]} />
        <Filter label={t('ov.filter.state')} value={loadedOnly} onChange={setLoadedOnly} width="w-36" options={[
          { id: 'all', label: t('ov.filter.state.all') },
          { id: 'loaded', label: t('ov.filter.state.loaded') },
          { id: 'used', label: t('ov.filter.state.used') },
          { id: 'unused', label: t('ov.filter.state.unused') },
          { id: 'behind', label: t('ov.filter.state.behind') },
          { id: 'risky', label: t('ov.filter.state.risky') },
        ]} />
        <span className="ml-auto text-sm text-foreground/60">
          {t('ov.results', { n: sorted.length })}
        </span>
      </div>

      <Table className="w-full">
        <Table.ScrollContainer>
          <Table.Content
            aria-label={t('ov.table')}
            sortDescriptor={sort}
            onSortChange={(d) => setSort(d as SortDesc)}
            onRowAction={(k) => {
              const hit = filtered.find((x) => x.key === String(k));
              if (hit) setSel(hit);
            }}
          >
            <Table.Header>
              <Table.Column id="name" isRowHeader allowsSorting>
                {({ sortDirection }) => (
                  <Table.SortableColumnHeader sortDirection={sortDirection}>
                    {t('ov.col.skill')}
                  </Table.SortableColumnHeader>
                )}
              </Table.Column>
              <Table.Column id="source">{t('ov.col.source')}</Table.Column>
              <Table.Column id="agents">{t('ov.col.agents')}</Table.Column>
              <Table.Column id="installs" allowsSorting>
                {({ sortDirection }) => (
                  <Table.SortableColumnHeader sortDirection={sortDirection}>
                    {t('ov.col.installs')}
                  </Table.SortableColumnHeader>
                )}
              </Table.Column>
              <Table.Column id="total" allowsSorting>
                {({ sortDirection }) => (
                  <Table.SortableColumnHeader sortDirection={sortDirection}>
                    {t('ov.col.usage')}
                  </Table.SortableColumnHeader>
                )}
              </Table.Column>
              <Table.Column id="d7" allowsSorting>
                {({ sortDirection }) => (
                  <Table.SortableColumnHeader sortDirection={sortDirection}>
                    {t('ov.col.d7')}
                  </Table.SortableColumnHeader>
                )}
              </Table.Column>
              <Table.Column id="last" allowsSorting>
                {({ sortDirection }) => (
                  <Table.SortableColumnHeader sortDirection={sortDirection}>
                    {t('ov.col.last')}
                  </Table.SortableColumnHeader>
                )}
              </Table.Column>
            </Table.Header>
            <Table.Body
              renderEmptyState={() => (
                <div className="p-10 text-center text-foreground/60">{t('ov.empty')}</div>
              )}
            >
              {sorted.map((it) => (
                <Table.Row key={it.key} id={it.key} className="cursor-pointer">
                  <Table.Cell>
                    <div className="max-w-96">
                      <div className="flex items-center gap-1.5">
                        <span className="truncate font-medium">{it.name}</span>
                        {!it.in_library && (
                          <Chip size="sm" className="shrink-0 bg-foreground/10 text-foreground/60">
                            {t(it.source === 'unmanaged' ? 'ov.chip.unmanaged' : 'ov.chip.external')}
                          </Chip>
                        )}
                        {it.vetting?.top_severity === 'high' && (
                          <Chip size="sm" className="shrink-0 bg-red-500/15 text-red-700 dark:text-red-300">
                            {t('ov.chip.high')}
                          </Chip>
                        )}
                        {it.update?.state === 'behind' && (
                          <Chip size="sm" className="shrink-0 bg-amber-500/15 text-amber-700 dark:text-amber-300">
                            {t('ov.chip.update')}
                          </Chip>
                        )}
                      </div>
                      {it.id && it.id !== it.name && (
                        <div className="truncate font-mono text-xs text-foreground/60"
                             title={it.library_path || it.id}>{it.id}</div>
                      )}
                      {it.tags.length > 0 && (
                        <div className="mt-0.5 flex gap-1">
                          {it.tags.map((tag) => (
                            <span key={tag} className="rounded bg-sky-500/10 px-1 text-[11px] text-sky-700 dark:text-sky-300">
                              {categoryLabel(tag)}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </Table.Cell>
                  <Table.Cell>
                    <span className="whitespace-nowrap text-sm text-foreground/70">
                      {sourceLabel(it.source)}
                    </span>
                  </Table.Cell>
                  <Table.Cell>
                    <AgentChips agents={it.agents} usage={it.agent_usage} />
                  </Table.Cell>
                  <Table.Cell>
                    {it.installs.length > 0 ? (
                      <span className="tabular-nums cursor-help"
                            title={it.installs
                              .map((i) => `${i.host} · ${t(i.scope === 'global' ? 'common.global' : 'common.project')} · ${prettyPath(i.entry_path)}`)
                              .join('\n')}>
                        {it.installs.length}
                        <span className="ml-1 text-xs text-foreground/60">
                          {' '}{t('ov.installs.split', {
                            g: it.installs.filter((i) => i.scope === 'global').length,
                            p: it.installs.filter((i) => i.scope === 'project').length,
                          })}
                        </span>
                      </span>
                    ) : <span className="text-foreground/50">—</span>}
                  </Table.Cell>
                  <Table.Cell><span className="tabular-nums font-medium">{it.usage.total || '—'}</span></Table.Cell>
                  <Table.Cell><span className="tabular-nums">{it.usage.d7 || '—'}</span></Table.Cell>
                  <Table.Cell>
                    <span className="text-sm text-foreground/60">{fmtRel(it.usage.last)}</span>
                  </Table.Cell>
                </Table.Row>
              ))}
            </Table.Body>
          </Table.Content>
        </Table.ScrollContainer>
      </Table>

      <SkillDrawer item={sel} libraryRoot={tiles?.library_root ?? ''}
                   onClose={() => setSel(null)} />
    </div>
  );
}
