import { useMemo, useState, type ReactElement } from 'react';
import {
  Button, Card, Chip, Label, ListBox, SearchField, Select, Spinner, Switch,
} from '@heroui/react';
import {
  agentLabel, useApi, sourceLabel, type Install, type SkillItem, type Tiles,
} from '../lib/api';
import { PathChain } from '../lib/paths';
import { LinkDocToggle } from '../lib/linkDoc';
import { Segmented } from '../components/Segmented';
import { categoryLabel, t, useT, vendorLabel, type MsgKey } from '../lib/i18n';

/* Colors carry ONE job here: how a skill is attached. The split matters for
 * governance: a copy committed inside someone's repo is not the same finding as
 * a copy nobody owns. Vendored copies are informational rather than a problem,
 * so they take the categorical blue slot, not a status hue.
 *
 * The symlink series is GREEN (user request, 2026-09-02) — the healthy majority reads as
 * healthy. In light mode it keeps the de-emphasis wash (.40 alpha), which also
 * resolves the classic green↔orange deutan trap through lightness: effective
 * post-alpha colors validate at ΔE ≥ 11.5 all-pairs CVD. Dark mode CANNOT use
 * the wash — a dimmed green lands on the dark red's lightness and protan ΔE
 * collapses to ~2 — so dark green is opaque #38e1b9, which the ribbons' own
 * 0.72 opacity lands at #2fa98c: green↔orange 9.6 deutan / 12.2 tritan, clean.
 * The one sub-floor pair either mode is the pre-existing orange↔red
 * (~12.5 normal-vision), relieved by legend + hover tooltip + table view.
 * Values live in styles.css (:root) because the health-page explainer shares
 * them; numbers from a CVD palette validator on the effective colors. */
const LINK_KINDS = [
  { key: 'symlink', label: 'link.symlink', color: 'var(--sh-link-ok)',
    note: 'link.note.symlink' },
  { key: 'vendored', label: 'link.vendored', color: 'var(--sh-link-vendored)',
    note: 'link.note.vendored' },
  { key: 'entity', label: 'link.entity', color: '#ec835a',
    note: 'link.note.entity' },
  { key: 'broken', label: 'link.broken', color: '#d03b3b',
    note: 'link.note.broken' },
] as const satisfies readonly {
  key: string; label: MsgKey; color: string; note: MsgKey;
}[];

const COLOR_OF: Record<string, string> = Object.fromEntries(
  LINK_KINDS.map((k) => [k.key, k.color]));

type GroupBy = 'tag' | 'vendor' | 'source';
const GROUP_KEY: Record<GroupBy, MsgKey> = {
  tag: 'to.group.tag', vendor: 'to.group.vendor', source: 'to.group.source',
};
/** Group headings double as node ids, so they are resolved (not keyed) here —
 * two groups must never collapse into one because they share a key. */
const groupName = (by: GroupBy) => t(GROUP_KEY[by]);

/* One screen per level of the hierarchy, held in a history stack so the view can
 * be stepped back and forth like pages — a drill-down that only goes deeper
 * forces people back to the top whenever they change their mind. */
type View =
  | { kind: 'groups'; by: GroupBy }
  | { kind: 'group'; by: GroupBy; value: string }
  | { kind: 'skill'; key: string; name: string };

type Flow = { from: string; to: string; kind: string; count: number };
type RightMeta = {
  agent: string; scope: string; project: string; sharedWith: string;
};
type Node = { id: string; total: number; y: number; h: number };

/* The folded node is a synthetic left-hand id, not a skill: it must stay
 * recognisable later (it is not clickable), so it carries a marker prefix
 * instead of being matched by its own translated text. */
const FOLDED_PREFIX = '\u0002folded:';

const NODE_W = 168;
const ROW_GAP = 6;
const MIN_H = 3;
const PAD_Y = 10;
const LABEL_MIN_GAP = 30;
const NAME_CAP = 40;

function layout(ids: string[], totals: Map<string, number>, height: number) {
  const sum = ids.reduce((a, id) => a + (totals.get(id) ?? 0), 0) || 1;
  const usable = Math.max(40, height - PAD_Y * 2 - ROW_GAP * Math.max(0, ids.length - 1));
  const out = new Map<string, Node>();
  let y = PAD_Y;
  for (const id of ids) {
    const total = totals.get(id) ?? 0;
    const h = Math.max(MIN_H, (total / sum) * usable);
    out.set(id, { id, total, y, h });
    y += h + ROW_GAP;
  }
  return out;
}

function ribbon(x0: number, y0: number, x1: number, y1: number, t0: number, t1: number) {
  const cx = (x0 + x1) / 2;
  return `M${x0},${y0} C${cx},${y0} ${cx},${y1} ${x1},${y1} `
    + `L${x1},${y1 + t1} C${cx},${y1 + t1} ${cx},${y0 + t0} ${x0},${y0 + t0} Z`;
}

function clip(s: string, n: number) {
  return s.length > n ? s.slice(0, n - 1) + '…' : s;
}

/* Node heights stay strictly proportional, which leaves the smallest nodes a few
 * pixels tall — far less than a two-line label needs. Labels therefore get their
 * own placement: seeded at each node's centre, pushed apart forward, then pulled
 * back inside the canvas from the bottom. */
function labelYs(nodes: Node[], height: number,
                 gaps?: number[]): Map<string, number> {
  // gaps[i] is the minimum distance from label i-1 to label i. A row that opens
  // a tool block needs more room above it than a plain row, because its heading
  // (and, for a shared directory, the line naming who shares it) is drawn there.
  const gapAt = (i: number) => gaps?.[i] ?? LABEL_MIN_GAP;
  const top = 14;
  const bottom = height - 14;
  const ys = nodes.map((n) => n.y + n.h / 2);
  for (let i = 1; i < ys.length; i++) {
    ys[i] = Math.max(ys[i], ys[i - 1] + gapAt(i));
  }
  if (ys.length) ys[ys.length - 1] = Math.min(ys[ys.length - 1], bottom);
  for (let i = ys.length - 2; i >= 0; i--) {
    ys[i] = Math.min(ys[i], ys[i + 1] - gapAt(i + 1));
  }
  if (ys.length) ys[0] = Math.max(ys[0], top);
  for (let i = 1; i < ys.length; i++) {
    ys[i] = Math.max(ys[i], ys[i - 1] + gapAt(i));
  }
  return new Map(nodes.map((n, i) => [n.id, ys[i]]));
}

function groupOf(it: SkillItem, by: GroupBy): string {
  if (by === 'vendor') return vendorLabel(it.category) || t('common.uncategorized');
  if (by === 'source') return sourceLabel(it.source);
  return it.tags[0] ? categoryLabel(it.tags[0]) : t('common.uncategorized');
}

export default function Topology() {
  const t = useT();
  const { data: skills } = useApi<{ items: SkillItem[] }>('/skills');
  const { data: tilesData } = useApi<Tiles>('/stats/tiles');
  const items = skills?.items ?? null;
  const libraryRoot = tilesData?.library_root ?? '';
  const [q, setQ] = useState('');
  const [tool, setTool] = useState('all');
  const [problemsOnly, setProblemsOnly] = useState(false);
  const [asTable, setAsTable] = useState(false);
  const [hover, setHover] = useState<Flow | null>(null);

  const [hist, setHist] = useState<View[]>([{ kind: 'groups', by: 'tag' }]);
  const [idx, setIdx] = useState(0);
  const view = hist[idx];

  const go = (v: View) => {
    const next = [...hist.slice(0, idx + 1), v];
    setHist(next);
    setIdx(next.length - 1);
    setHover(null);
  };
  const jumpTo = (i: number) => { setIdx(i); setHover(null); };


  const toolOptions = useMemo(() => {
    const s = new Map<string, number>();
    for (const it of items ?? []) {
      for (const ins of it.installs) s.set(ins.agent, (s.get(ins.agent) ?? 0) + 1);
    }
    return [...s.entries()].sort((a, b) => b[1] - a[1]);
  }, [items]);

  const model = useMemo(() => {
    const needle = q.trim().toLowerCase();
    const all = (items ?? []).filter((it) => it.installs.length > 0);
    const inView = all.filter((it) => {
      if (view.kind === 'group' && groupOf(it, view.by) !== view.value) return false;
      if (view.kind === 'skill' && it.key !== view.key) return false;
      if (!needle) return true;
      return `${it.key} ${it.name} ${it.description}`.toLowerCase().includes(needle);
    });

    const f = new Map<string, Flow>();
    const detail: Install[] = [];
    // right-hand nodes need more than a name: which tool, which scope, which
    // project, and — for a directory several tools read — who shares it
    const meta = new Map<string, RightMeta>();
    for (const it of inView) {
      it.installs.forEach((ins, i) => {
        if (tool !== 'all' && ins.agent !== tool) return;
        // "problems only" hides both healthy states: a symlink and a copy that
        // its own repo maintains
        if (problemsOnly && (ins.link_type === 'symlink' || ins.vcs === 'vendored')) return;
        // the deepest level names each entry, so one skill loaded twice into the
        // same tool still reads as two distinct destinations
        const from = view.kind === 'groups' ? groupOf(it, view.by) : it.name;
        const proj = ins.project_path ? ins.project_path.split('/').pop() ?? '' : '';
        const to = view.kind === 'skill'
          ? `${ins.agent}\u0001${ins.scope}\u0001${proj}\u0001${i}`
          : `${ins.agent}\u0001${ins.scope}\u0001\u0001`;
        if (!meta.has(to)) {
          meta.set(to, {
            agent: ins.agent, scope: ins.scope, project: proj,
            sharedWith: ins.shared_with || '',
          });
        }
        const kind = ins.link_type === 'entity'
          ? (ins.vcs === 'vendored' ? 'vendored' : 'entity')
          : ins.link_type;
        const key = `${from}${to}${kind}`;
        const prev = f.get(key);
        if (prev) prev.count += 1;
        else f.set(key, { from, to, kind, count: 1 });
        if (view.kind === 'skill') detail.push(ins);
      });
    }

    let list = [...f.values()];
    const seen = new Map<string, number>();
    for (const fl of list) seen.set(fl.from, (seen.get(fl.from) ?? 0) + fl.count);
    // Naming every skill would be a canvas nobody can read. Keep the busiest,
    // fold the rest into one labelled node — never silently drop.
    let folded = 0;
    if (view.kind !== 'groups' && seen.size > NAME_CAP) {
      const keep = new Set([...seen.entries()]
        .sort((a, b) => b[1] - a[1]).slice(0, NAME_CAP).map(([k]) => k));
      folded = seen.size - keep.size;
      const merged = new Map<string, Flow>();
      for (const fl of list) {
        const from = keep.has(fl.from) ? fl.from : FOLDED_PREFIX + folded;
        const k = `${from}${fl.to}${fl.kind}`;
        const p = merged.get(k);
        if (p) p.count += fl.count;
        else merged.set(k, { ...fl, from });
      }
      list = [...merged.values()];
    }

    const lt = new Map<string, number>();
    const rt = new Map<string, number>();
    for (const fl of list) {
      lt.set(fl.from, (lt.get(fl.from) ?? 0) + fl.count);
      rt.set(fl.to, (rt.get(fl.to) ?? 0) + fl.count);
    }
    return {
      flows: list, folded, detail, meta, matched: inView.length,
      leftIds: [...lt.keys()].sort((a, b) => (lt.get(b)! - lt.get(a)!)),
      // keep a tool's rows adjacent so they can be drawn as one block, and put
      // global before project inside it
      rightIds: [...rt.keys()].sort((a, b) => {
        const ma = meta.get(a); const mb = meta.get(b);
        if (ma && mb && ma.agent !== mb.agent) {
          const ta = [...rt.entries()].filter(([k]) => meta.get(k)?.agent === ma.agent)
            .reduce((x, [, v]) => x + v, 0);
          const tb = [...rt.entries()].filter(([k]) => meta.get(k)?.agent === mb.agent)
            .reduce((x, [, v]) => x + v, 0);
          if (ta !== tb) return tb - ta;
          return ma.agent.localeCompare(mb.agent);
        }
        if (ma && mb && ma.scope !== mb.scope) return ma.scope === 'global' ? -1 : 1;
        return (ma?.project ?? '').localeCompare(mb?.project ?? '');
      }),
      totalsL: lt, totalsR: rt,
      skillOf: new Map(inView.map((it) => [it.name, it])),
    };
  }, [items, q, tool, problemsOnly, view]);

  /** Left-hand node ids are display values already, except the synthetic
   * folded node, which carries a count to render. */
  const leftLabel = (id: string) =>
    (id.startsWith(FOLDED_PREFIX)
      ? t('to.foldedNode', { n: id.slice(FOLDED_PREFIX.length) })
      : id);

  const rightLabel = (id: string) => {
    const m = model.meta.get(id);
    if (!m) return { main: id, sub: '' };
    return {
      main: agentLabel(m.agent),
      sub: m.scope === 'global' ? t('common.global')
        : m.project ? t('to.scope.project', { name: m.project }) : t('common.project'),
    };
  };

  if (!items) {
    return <div className="flex justify-center py-20"><Spinner aria-label={t('common.loading')} /></div>;
  }

  const { flows, folded, detail, matched, leftIds, rightIds, totalsL, totalsR } = model;
  const rows = Math.max(leftIds.length, rightIds.length);
  const headerTotal = rightIds.reduce((a, id, k) => {
    const prev = k > 0 ? model.meta.get(rightIds[k - 1])?.agent : undefined;
    if (k > 0 && prev === model.meta.get(id)?.agent) return a;
    return a + (model.meta.get(id)?.sharedWith ? 30 : 16);
  }, 0);
  const H = Math.max(320, rows * LABEL_MIN_GAP + headerTotal + 56);
  const W = 900;
  const left = layout(leftIds, totalsL, H);
  const right = layout(rightIds, totalsR, H);

  const offL = new Map<string, number>();
  const offR = new Map<string, number>();
  const ordered = [...flows].sort((a, b) => b.count - a.count);
  const paths = ordered.map((f) => {
    const L = left.get(f.from);
    const R = right.get(f.to);
    if (!L || !R) return null;
    const tL = (f.count / (totalsL.get(f.from) || 1)) * L.h;
    const tR = (f.count / (totalsR.get(f.to) || 1)) * R.h;
    const y0 = L.y + (offL.get(f.from) ?? 0);
    const y1 = R.y + (offR.get(f.to) ?? 0);
    offL.set(f.from, (offL.get(f.from) ?? 0) + tL);
    offR.set(f.to, (offR.get(f.to) ?? 0) + tR);
    const gap = tL > 4 && tR > 4 ? 1 : 0;
    const thick = Math.max(1, tR - gap);
    return {
      f,
      d: ribbon(NODE_W, y0, W - NODE_W, y1, Math.max(1, tL - gap), thick),
      // a filled ribbon reads as a band, not a direction — a chevron at the
      // receiving end says which way the link points
      arrow: (() => {
        const x = W - NODE_W;
        const cy = y1 + thick / 2;
        const half = Math.min(5, Math.max(2.5, thick / 2));
        return `M${x - 9},${cy - half} L${x - 1},${cy} L${x - 9},${cy + half} Z`;
      })(),
    };
  }).filter(Boolean) as { f: Flow; d: string; arrow: string }[];

  const leftLabelY = labelYs(leftIds.map((id) => left.get(id)!), H);
  // reserve a slot above each tool block for its heading — plus a second line
  // when the directory is shared and needs to name who shares it
  const headerSpace = (k: number) => {
    const id = rightIds[k];
    const prevAgent = k > 0 ? model.meta.get(rightIds[k - 1])?.agent : undefined;
    if (k > 0 && prevAgent === model.meta.get(id)?.agent) return 0;
    return model.meta.get(id)?.sharedWith ? 30 : 16;
  };
  const rightGaps = rightIds.map((_, k) => LABEL_MIN_GAP + headerSpace(k));
  const rightLabelY = labelYs(
    rightIds.map((id, k) => {
      const n = right.get(id)!;
      const pad = headerSpace(k);
      return pad ? { ...n, y: n.y + pad } : n;
    }), H, rightGaps);
  const totalInstalls = flows.reduce((a, f) => a + f.count, 0);

  const onLeftClick = (id: string) => {
    if (id.startsWith(FOLDED_PREFIX)) return;
    if (view.kind === 'groups') go({ kind: 'group', by: view.by, value: id });
    else if (view.kind === 'group') {
      const it = model.skillOf.get(id);
      if (it) go({ kind: 'skill', key: it.key, name: it.name });
    }
  };
  const drillable = view.kind !== 'skill';

  const crumbs = hist.slice(0, idx + 1).map((v, i) => ({
    i,
    label: v.kind === 'groups' ? t('to.all', { by: groupName(v.by) })
      : v.kind === 'group' ? v.value : v.name,
  }));

  return (
    <div className="flex flex-col gap-4">
      {/* series color variables live in styles.css (:root) — the health-page
          explainer shares them, so they must not be scoped to this page */}

      <div className="flex flex-wrap items-center gap-2">
        <Button size="sm" variant="ghost" isDisabled={idx === 0}
          onPress={() => jumpTo(idx - 1)}>{t('to.back')}</Button>
        <Button size="sm" variant="ghost" isDisabled={idx >= hist.length - 1}
          onPress={() => jumpTo(idx + 1)}>{t('to.forward')}</Button>
        <nav className="flex flex-wrap items-center gap-1 text-sm" aria-label={t('to.breadcrumb')}>
          {crumbs.map((c, i) => (
            <span key={c.i} className="flex items-center gap-1">
              {i > 0 && <span className="text-foreground/30">›</span>}
              {i === crumbs.length - 1 ? (
                <span className="font-medium">{c.label}</span>
              ) : (
                <button type="button" onClick={() => jumpTo(c.i)}
                  className="text-foreground/60 underline-offset-2 hover:underline">
                  {c.label}
                </button>
              )}
            </span>
          ))}
        </nav>
        <span className="ml-auto text-sm text-foreground/60">
          {t('to.summary', { skills: matched, loads: totalInstalls })}
        </span>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <SearchField aria-label={t('ov.search')} value={q} onChange={setQ} className="w-64">
          <SearchField.Group>
            <SearchField.SearchIcon />
            <SearchField.Input placeholder={t('ov.search')} />
            <SearchField.ClearButton />
          </SearchField.Group>
        </SearchField>
        {view.kind === 'groups' && (
          <Select aria-label={t('to.groupBy.label')} selectedKey={view.by}
            onSelectionChange={(k) => { setHist([{ kind: 'groups', by: k as GroupBy }]); setIdx(0); }}
            className="w-44">
            <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
            <Select.Popover>
              <ListBox>
                {(['tag', 'vendor', 'source'] as GroupBy[]).map((g) => (
                  <ListBox.Item key={g} id={g}
                                textValue={t('to.groupBy', { by: groupName(g) })}>
                    <Label>{t('to.groupBy', { by: groupName(g) })}</Label>
                    <ListBox.ItemIndicator />
                  </ListBox.Item>
                ))}
              </ListBox>
            </Select.Popover>
          </Select>
        )}
        <Select aria-label={t('ov.filter.tool')} selectedKey={tool}
          onSelectionChange={(k) => setTool(String(k))} className="w-48">
          <Select.Trigger><Select.Value /><Select.Indicator /></Select.Trigger>
          <Select.Popover>
            <ListBox>
              <ListBox.Item id="all" textValue={t('ov.filter.tool.all')}>
                <Label>{t('ov.filter.tool.all')}</Label><ListBox.ItemIndicator />
              </ListBox.Item>
              {toolOptions.map(([a, n]) => (
                <ListBox.Item key={a} id={a} textValue={agentLabel(a)}>
                  <Label>{`${agentLabel(a)} (${n})`}</Label><ListBox.ItemIndicator />
                </ListBox.Item>
              ))}
            </ListBox>
          </Select.Popover>
        </Select>
        <Switch isSelected={problemsOnly} onChange={setProblemsOnly}>
          <Switch.Content>
            <Switch.Control><Switch.Thumb /></Switch.Control>
            {t('to.problemsOnly')}
          </Switch.Content>
        </Switch>
        <Segmented
          label={t('to.view')}
          value={asTable ? 'table' : 'chart'}
          onChange={(v) => setAsTable(v === 'table')}
          options={[
            { id: 'chart', label: t('to.view.chart') },
            { id: 'table', label: t('to.view.table') },
          ]}
        />
      </div>

      <div className="flex flex-wrap items-center gap-4 gap-y-2">
        {LINK_KINDS.map((k) => (
          <span key={k.key} className="sh-topo flex items-center gap-1.5" title={t(k.note)}>
            <span className="h-2.5 w-5 rounded-sm" style={{ background: k.color }} />
            <span className="text-xs text-foreground/70">{t(k.label)}</span>
          </span>
        ))}
        <LinkDocToggle />
        <span className="text-xs text-foreground/60">
          {view.kind === 'groups' ? t('to.hint.groups', { by: groupName(view.by) })
            : view.kind === 'group' ? t('to.hint.group')
              : t('to.hint.skill')}
          {folded > 0 ? t('to.folded', { n: folded }) : ''}
        </span>
      </div>

      <Card>
        <Card.Content className="p-3">
          {flows.length === 0 ? (
            <p className="py-16 text-center text-sm text-foreground/60">{t('to.empty')}</p>
          ) : asTable ? (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-foreground/10 text-left text-xs text-foreground/60">
                    <th className="py-1.5 pr-3 font-medium">
                      {view.kind === 'groups' ? groupName(view.by) : t('to.col.skill')}
                    </th>
                    <th className="py-1.5 pr-3 font-medium">{t('to.col.tool')}</th>
                    <th className="py-1.5 pr-3 font-medium">{t('to.col.scope')}</th>
                    <th className="py-1.5 pr-3 font-medium">{t('to.col.kind')}</th>
                    <th className="py-1.5 font-medium">{t('to.col.count')}</th>
                  </tr>
                </thead>
                <tbody>
                  {ordered.map((f, i) => {
                    const r = rightLabel(f.to);
                    const k = LINK_KINDS.find((x) => x.key === f.kind);
                    return (
                      <tr key={i} className="border-b border-foreground/5">
                        <td className="py-1.5 pr-3">{leftLabel(f.from)}</td>
                        <td className="py-1.5 pr-3">{r.main}</td>
                        <td className="py-1.5 pr-3 text-foreground/65">{r.sub}</td>
                        <td className="py-1.5 pr-3 sh-topo">
                          <span className="inline-flex items-center gap-1.5">
                            <span className="h-2 w-3 rounded-sm"
                              style={{ background: k?.color }} />
                            {k ? t(k.label) : f.kind}
                          </span>
                        </td>
                        <td className="py-1.5 tabular-nums">{f.count}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="overflow-x-auto sh-topo">
              <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}
                role="img" aria-label={t('to.chart')}
                onMouseLeave={() => setHover(null)}>
                {paths.map((p, i) => (
                  <g key={i} onMouseEnter={() => setHover(p.f)}
                    opacity={hover && hover !== p.f ? 0.15 : 1}
                    style={{ transition: 'opacity .12s' }}>
                    <path d={p.d} fill={COLOR_OF[p.f.kind]} opacity={0.72} />
                    <path d={p.arrow} fill={COLOR_OF[p.f.kind]} />
                  </g>
                ))}
                {leftIds.map((id) => {
                  const n = left.get(id)!;
                  const ly = leftLabelY.get(id)!;
                  const off = Math.abs(ly - (n.y + n.h / 2)) > 6;
                  const canDrill = drillable && !id.startsWith(FOLDED_PREFIX);
                  return (
                    <g key={id} style={{ cursor: canDrill ? 'pointer' : 'default' }}
                      onClick={canDrill ? () => onLeftClick(id) : undefined}>
                      <rect x={NODE_W - 5} y={n.y} width={5} height={n.h} rx={1.5}
                        className={canDrill ? 'fill-foreground/60' : 'fill-foreground/45'} />
                      {off && (
                        <line x1={NODE_W - 7} y1={n.y + n.h / 2} x2={NODE_W - 11} y2={ly}
                          className="stroke-foreground/20" strokeWidth={1} />
                      )}
                      <text x={NODE_W - 14} y={ly - 5} textAnchor="end"
                        className="fill-foreground text-[12px]"
                        style={canDrill ? { textDecoration: 'underline',
                          textUnderlineOffset: 3, textDecorationColor: 'rgb(128 128 128 / .5)' } : undefined}>
                        {clip(leftLabel(id), 24)}
                      </text>
                      <text x={NODE_W - 14} y={ly + 9} textAnchor="end"
                        className="fill-foreground/45 text-[10px]">{n.total}</text>
                    </g>
                  );
                })}
                {(() => {
                  // draw the right column as tool blocks: one bold heading per
                  // tool with a bracket down its rows, and each row naming only
                  // its scope / project — "Codex" once, not on every line
                  const out: ReactElement[] = [];
                  let i = 0;
                  while (i < rightIds.length) {
                    const agent = model.meta.get(rightIds[i])?.agent ?? rightIds[i];
                    let j = i;
                    while (j < rightIds.length
                      && (model.meta.get(rightIds[j])?.agent ?? rightIds[j]) === agent) j++;
                    const groupIds = rightIds.slice(i, j);
                    const ys = groupIds.map((g) => rightLabelY.get(g)!);
                    const shared0 = model.meta.get(groupIds[0])?.sharedWith ?? '';
                    const top = Math.min(...ys) - (shared0 ? 30 : 16);
                    const bot = Math.max(...ys) + 6;
                    const shared = model.meta.get(groupIds[0])?.sharedWith ?? '';
                    const total = groupIds.reduce(
                      (a, g) => a + (right.get(g)?.total ?? 0), 0);
                    const x = W - NODE_W;
                    out.push(
                      <g key={`g-${agent}`}>
                        <line x1={x + 10} y1={top + 4} x2={x + 10} y2={bot}
                          className="stroke-foreground/15" strokeWidth={1} />
                        <text x={x + 16} y={top + 10}
                          className="fill-foreground text-[12.5px] font-medium">
                          {clip(agentLabel(agent), 22)}
                        </text>

                        {shared && (
                          <title>{t('to.sharedBy', { list: shared })}</title>
                        )}
                      </g>,
                    );
                    if (shared) {
                      out.push(
                        <text key={`s-${agent}`} x={x + 16} y={top + 22}
                          className="fill-foreground/45 text-[9.5px]">
                          {clip(t('to.sharedCount',
                            { n: shared.split(', ').length, list: shared }), 40)}
                        </text>,
                      );
                    }
                    for (const gid of groupIds) {
                      const n = right.get(gid)!;
                      const ly = rightLabelY.get(gid)!;
                      const r = rightLabel(gid);
                      const off = Math.abs(ly - (n.y + n.h / 2)) > 6;
                      out.push(
                        <g key={gid}>
                          <rect x={x} y={n.y} width={5} height={n.h} rx={1.5}
                            className="fill-foreground/45" />
                          {off && (
                            <line x1={x + 7} y1={n.y + n.h / 2} x2={x + 10} y2={ly}
                              className="stroke-foreground/20" strokeWidth={1} />
                          )}
                          <text x={x + 18} y={ly + 4}
                            className="fill-foreground/70 text-[11px]">
                            {clip(r.sub, 24)}
                            {view.kind === 'skill' ? '' : ` · ${n.total}`}
                          </text>
                        </g>,
                      );
                    }
                    i = j;
                  }
                  return out;
                })()}
              </svg>
            </div>
          )}
        </Card.Content>
      </Card>

      {view.kind === 'skill' && detail.length > 0 && (
        <Card>
          <Card.Header className="pb-2">
            <Card.Title className="text-base">
              {t('to.detail.title', { n: detail.length })}
            </Card.Title>
            <Card.Description>{t('to.detail.desc')}</Card.Description>
          </Card.Header>
          <Card.Content>
            <ul className="flex flex-col gap-2.5">
              {detail.map((ins, i) => (
                <li key={i} className="border-b border-foreground/5 pb-2 last:border-0">
                  <div className="mb-1 flex flex-wrap items-center gap-1.5">
                    <Chip size="sm" className="bg-foreground/10">{agentLabel(ins.agent)}</Chip>
                    <Chip size="sm" className={ins.scope === 'global'
                      ? 'bg-violet-500/15 text-violet-700 dark:text-violet-300'
                      : 'bg-foreground/10 text-foreground/65'}>
                      {t(ins.scope === 'global' ? 'common.global' : 'common.project')}
                    </Chip>
                    {(() => {
                      const k = ins.link_type === 'entity'
                        ? (ins.vcs === 'vendored' ? 'vendored' : 'entity')
                        : ins.link_type;
                      const meta = LINK_KINDS.find((x) => x.key === k);
                      return (
                        <span className="sh-topo inline-flex items-center gap-1.5 text-xs"
                          title={meta?.note}>
                          <span className="h-2 w-3 rounded-sm"
                            style={{ background: COLOR_OF[k] }} />
                          {meta ? t(meta.label) : k}
                        </span>
                      );
                    })()}
                    <span className="text-xs text-foreground/60">{ins.host}</span>
                  </div>
                  <PathChain from={ins.entry_path} to={ins.target_path}
                    libraryRoot={libraryRoot} />
                </li>
              ))}
            </ul>
          </Card.Content>
        </Card>
      )}

      <div className="min-h-[2.5rem]">
        {hover && (
          <div className="sh-topo rounded-lg border border-foreground/10 bg-foreground/[0.03] px-3 py-2 text-sm">
            <span className="font-medium">{leftLabel(hover.from)}</span>
            <span className="mx-2 text-foreground/40">{'→'}</span>
            <span>{rightLabel(hover.to).main}</span>
            <span className="ml-1 text-foreground/60"> ({rightLabel(hover.to).sub})</span>
            <span className="mx-2 inline-flex items-center gap-1.5">
              <span className="h-2 w-3 rounded-sm"
                style={{ background: COLOR_OF[hover.kind] }} />
              {(() => {
                const hk = LINK_KINDS.find((x) => x.key === hover.kind);
                return hk ? t(hk.label) : hover.kind;
              })()}
            </span>
            <span className="tabular-nums text-foreground/70">
              {t('to.hover.count', { n: hover.count })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
