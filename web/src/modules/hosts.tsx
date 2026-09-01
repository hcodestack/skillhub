import { Card, Spinner } from '@heroui/react';
import { fmtRel, useApi, AGENT_LABEL, type HostRow } from '../lib/api';

export default function Hosts() {
  const { data } = useApi<{ hosts: HostRow[] }>('/hosts');
  const hosts = data?.hosts ?? null;

  if (!hosts) {
    return <div className="flex justify-center py-20"><Spinner aria-label="加载中" /></div>;
  }
  if (!hosts.length) {
    return <p className="py-16 text-center text-foreground/60">还没有主机上报过数据。</p>;
  }
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {hosts.map((h) => (
        <Card key={h.id}>
          <Card.Header>
            <Card.Title>{h.id}</Card.Title>
            <Card.Description>
              {h.os} · 最近上报 {fmtRel(h.last_report_at)}
            </Card.Description>
          </Card.Header>
          <Card.Content>
            <div className="flex flex-col gap-1.5 text-sm">
              {h.agents.map((a) => (
                <div key={a.agent} className="flex items-baseline justify-between">
                  <span>{AGENT_LABEL[a.agent] ?? a.agent}</span>
                  <span className="tabular-nums text-foreground/60">
                    {a.entries} 入口（全局 {a.global_entries} / 项目 {a.project_entries}）
                  </span>
                </div>
              ))}
              <div className="mt-1 flex items-baseline justify-between border-t border-foreground/10 pt-1.5">
                <span>累计调用</span>
                <span className="tabular-nums">{h.events_total}</span>
              </div>
            </div>
          </Card.Content>
        </Card>
      ))}
    </div>
  );
}
