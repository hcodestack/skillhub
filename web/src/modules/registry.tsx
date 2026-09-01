import type { ComponentType } from 'react';
import Overview from './overview';
import Health from './health';
import Updates from './updates';
import Topology from './topology';
import Hosts from './hosts';

// 模块化：增删 Dashboard 模块只改这个数组。
export const MODULES: { key: string; label: string; component: ComponentType }[] = [
  { key: 'overview', label: '总览', component: Overview },
  { key: 'topology', label: '拓扑', component: Topology },
  { key: 'updates', label: '更新', component: Updates },
  { key: 'health', label: '健康', component: Health },
  { key: 'hosts', label: '主机', component: Hosts },
];
