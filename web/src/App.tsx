import { useEffect, useState } from 'react';
import { Switch, Tabs } from '@heroui/react';
import { MODULES } from './modules/registry';

function useTheme() {
  const [dark, setDark] = useState(() =>
    document.documentElement.classList.contains('dark'));
  const toggle = (v: boolean) => {
    setDark(v);
    document.documentElement.classList.toggle('dark', v);
    document.documentElement.dataset.theme = v ? 'dark' : 'light';
    localStorage.setItem('skillhub-theme', v ? 'dark' : 'light');
  };
  return { dark, toggle };
}

// The URL hash carries navigation state: `#health` selects a tab,
// `#health/broken_links` additionally targets a section inside it. Before
// this, a refresh always dumped the user back on 总览 and there was no way to
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

export default function App() {
  const { dark, toggle } = useTheme();
  const { tab, select } = useHashTab();
  return (
    <div className="mx-auto max-w-7xl px-4 py-6 md:px-8">
      <header className="mb-6 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Skillhub</h1>
          <p className="text-sm text-foreground/60">
            本地技能总揽 — 库存 · 载入拓扑 · 调用记录
          </p>
        </div>
        <Switch isSelected={dark} onChange={toggle}>
          <Switch.Content>
            <Switch.Control>
              <Switch.Thumb />
            </Switch.Control>
            <span className="whitespace-nowrap">深色</span>
          </Switch.Content>
        </Switch>
      </header>

      <Tabs selectedKey={tab} onSelectionChange={(k) => select(String(k))}>
        <Tabs.ListContainer>
          <Tabs.List aria-label="模块">
            {MODULES.map((m) => (
              <Tabs.Tab key={m.key} id={m.key}>
                {m.label}
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
