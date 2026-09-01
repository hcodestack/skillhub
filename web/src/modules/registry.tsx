import type { ComponentType } from 'react';
import type { MsgKey } from '../lib/i18n';
import Overview from './overview';
import Health from './health';
import Updates from './updates';
import Topology from './topology';
import Hosts from './hosts';

// Modular: adding or removing a dashboard module means editing this array only.
// `label` is a message key, not display text — the tab strip is rendered by
// App.tsx, which translates it in the current language.
export const MODULES: { key: string; label: MsgKey; component: ComponentType }[] = [
  { key: 'overview', label: 'nav.overview', component: Overview },
  { key: 'topology', label: 'nav.topology', component: Topology },
  { key: 'updates', label: 'nav.updates', component: Updates },
  { key: 'health', label: 'nav.health', component: Health },
  { key: 'hosts', label: 'nav.hosts', component: Hosts },
];
