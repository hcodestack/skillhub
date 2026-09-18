import { useEffect, useState } from 'react';
import { Tabs } from '@heroui/react';
import { MODULES } from './modules/registry';
import { LangSwitch } from './components/LangSwitch';
import { Segmented } from './components/Segmented';
import { useApi, type SourceRow, type Tiles } from './lib/api';
import { useT } from './lib/i18n';

type Theme = 'system' | 'light' | 'dark';
const THEME_KEY = 'skillhub-theme';
const media = () => matchMedia('(prefers-color-scheme: dark)');

function applyTheme(theme: Theme) {
  const dark = theme === 'dark' || (theme === 'system' && media().matches);
  document.documentElement.classList.toggle('dark', dark);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
}

/* Three states, not two. The old switch stored light/dark on first touch and
 * could never go back to following the OS — a dashboard left open on a machine
 * that turns dark at sunset kept the daytime theme forever. "System" is the
 * absence of a stored choice, and while it is selected the OS change event is
 * honoured live. (Layout borrowed from skills-hub's Appearance control.) */
function useTheme() {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === 'light' || saved === 'dark' ? saved : 'system';
  });
  useEffect(() => {
    applyTheme(theme);
    if (theme !== 'system') return;
    const mq = media();
    const follow = () => applyTheme('system');
    mq.addEventListener('change', follow);
    return () => mq.removeEventListener('change', follow);
  }, [theme]);
  const choose = (next: Theme) => {
    setTheme(next);
    if (next === 'system') localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, next);
  };
  return { theme, choose };
}

// The URL hash carries navigation state: `#health` selects a tab,
// `#health/broken_links` additionally targets a section inside it. Before
// this, a refresh always dumped the user back on the overview and there was no way to
// hand someone a link to "the broken links list" — for a LAN dashboard whose
// findings get discussed across machines, the address bar is the cheapest
// deep-linking mechanism there is.
function hashTab(): string {
  const t = window.location.hash.slice(1).split('/')[0];
  return MODULES.some((m) => m.key === t) ? t : MODULES[0].key;
}

function useHashTab() {
  const [tab, setTab] = useState(hashTab);
  useEffect(() => {
    const onHash = () => setTab(hashTab());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);
  const select = (k: string) => {
    setTab(k);
    // replaceState keeps tab browsing out of the back-button history;
    // deep links written by tiles use location.hash and do push.
    history.replaceState(null, '', '#' + k);
  };
  return { tab, select };
}

/* A count on a tab answers "is there anything in there for me?" without a
 * visit — the same job the sidebar counts do in skills-hub. Only the two tabs
 * that hold actionable findings get one; a count of skills or hosts would be
 * noise. Both numbers come from endpoints the overview fetches anyway, so
 * this costs no extra request. */
function useTabCounts() {
  const { data: tiles } = useApi<Tiles>('/stats/tiles');
  const { data: sources } = useApi<{ items: SourceRow[] }>('/sources');
  const broken = tiles?.broken_links ?? 0;
  const health = broken + (tiles?.loose_entries ?? 0);
  const updates = sources?.items.filter((i) => i.state === 'behind').length ?? 0;
  return {
    health: { n: health, tone: broken > 0 ? 'error' : 'warn' },
    updates: { n: updates, tone: 'warn' },
  } as Record<string, { n: number; tone: 'error' | 'warn' }>;
}

function Count({ n, tone, title }: { n: number; tone: 'error' | 'warn'; title: string }) {
  if (!n) return null;
  const cls = tone === 'error'
    ? 'bg-red-500/15 text-red-700 dark:text-red-300'
    : 'bg-amber-500/15 text-amber-700 dark:text-amber-300';
  return (
    <span title={title}
          className={`ml-1.5 rounded-full px-1.5 py-px text-[11px] font-medium tabular-nums ${cls}`}>
      {n}
    </span>
  );
}

export default function App() {
  const { theme, choose } = useTheme();
  const { tab, select } = useHashTab();
  const counts = useTabCounts();
  const t = useT();
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <header className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Skillmgmnt</h1>
          <p className="text-sm text-foreground/60">{t('app.subtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <LangSwitch />
          <Segmented<Theme>
            label={t('app.theme')}
            value={theme}
            onChange={choose}
            options={[
              { id: 'system', label: t('app.theme.system') },
              { id: 'light', label: t('app.theme.light') },
              { id: 'dark', label: t('app.theme.dark') },
            ]}
          />
        </div>
      </header>

      <Tabs selectedKey={tab} onSelectionChange={(k) => select(String(k))}>
        <Tabs.ListContainer>
          <Tabs.List aria-label={t('app.modules')}>
            {MODULES.map((m) => (
              <Tabs.Tab key={m.key} id={m.key}>
                {t(m.label)}
                {counts[m.key] && (
                  <Count n={counts[m.key].n} tone={counts[m.key].tone}
                         title={t(m.key === 'health' ? 'app.badge.health' : 'app.badge.updates',
                                  { n: counts[m.key].n })} />
                )}
                <Tabs.Indicator />
              </Tabs.Tab>
            ))}
          </Tabs.List>
        </Tabs.ListContainer>
        {MODULES.map((m) => (
          <Tabs.Panel key={m.key} id={m.key} className="pt-5">
            <m.component />
          </Tabs.Panel>
        ))}
      </Tabs>
    </div>
  );
}
