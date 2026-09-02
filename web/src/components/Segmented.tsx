import { ToggleButton, ToggleButtonGroup } from '@heroui/react';

/* One control for every "pick exactly one of these views/modes" choice in the
 * dashboard: language, theme, chart-or-table. A switch is for a binary
 * *setting*; a mutually-exclusive *view* wants all its options visible at rest
 * so the alternative is one click away, not hidden behind an off state. (Rule
 * borrowed from qufei1993/skills-hub's UI guidelines, which we were breaking
 * on the topology page.) */
export function Segmented<K extends string>({ value, options, onChange, label }: {
  value: K;
  options: { id: K; label: string }[];
  onChange: (v: K) => void;
  label: string;
}) {
  return (
    <ToggleButtonGroup
      aria-label={label}
      size="sm"
      selectionMode="single"
      disallowEmptySelection
      selectedKeys={[value]}
      onSelectionChange={(keys) => {
        const k = [...keys][0];
        if (k != null) onChange(String(k) as K);
      }}
    >
      {options.map((o) => (
        <ToggleButton key={o.id} id={o.id} className="px-2.5 text-xs">
          {o.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}
