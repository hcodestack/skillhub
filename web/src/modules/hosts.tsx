import { Card, Spinner } from '@heroui/react';
import { agentLabel, fmtRel, useApi, type HostRow } from '../lib/api';
import { useT } from '../lib/i18n';
import { ToolIcon } from '../components/ToolIcon';

export default function Hosts() {
  const t = useT();
  const { data } = useApi<{ hosts: HostRow[] }>('/hosts');
  const hosts = data?.hosts ?? null;

  if (!hosts) {
    return <div className="flex justify-center py-20"><Spinner aria-label={t('common.loading')} /></div>;
  }
  if (!hosts.length) {
    return <p className="py-16 text-center text-foreground/60">{t('ho.none')}</p>;
  }
  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
      {hosts.map((h) => (
        <Card key={h.id}>
          <Card.Header>
            <Card.Title>{h.id}</Card.Title>
            <Card.Description>
              {h.os} · {t('ho.lastReport', { when: fmtRel(h.last_report_at) })}
            </Card.Description>
          </Card.Header>
          <Card.Content>
            <div className="flex flex-col gap-1.5 text-sm">
              {h.agents.map((a) => (
                <div key={a.agent} className="flex items-baseline justify-between">
                  <span className="inline-flex items-center gap-2">
                    <ToolIcon agent={a.agent} size={16} />
                    {agentLabel(a.agent)}
                  </span>
                  <span className="tabular-nums text-foreground/60">
                    {t('ho.entries', {
                      n: a.entries, g: a.global_entries, p: a.project_entries,
                    })}
                  </span>
                </div>
              ))}
              <div className="mt-1 flex items-baseline justify-between border-t border-foreground/10 pt-1.5">
                <span>{t('ho.total')}</span>
                <span className="tabular-nums">{h.events_total}</span>
              </div>
            </div>
          </Card.Content>
        </Card>
      ))}
    </div>
  );
}
