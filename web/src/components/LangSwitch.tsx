import { LANGS, setLang, useLang, useT } from '../lib/i18n';

/* A two-option choice belongs in a two-option control: a segmented pair of
 * buttons switches in one click and shows both states at rest, where a dropdown
 * would hide the alternative behind a menu. Sits next to the theme switch —
 * the header is where people already look for display preferences. */
export function LangSwitch() {
  const lang = useLang();
  const t = useT();
  return (
    <div
      role="group"
      aria-label={t('app.language')}
      className="flex shrink-0 overflow-hidden rounded-md border border-foreground/15"
    >
      {LANGS.map((l) => {
        const active = l.id === lang;
        return (
          <button
            key={l.id}
            type="button"
            lang={l.id === 'zh' ? 'zh-CN' : 'en'}
            aria-pressed={active}
            onClick={() => setLang(l.id)}
            className={`px-2 py-1 text-xs transition-colors ${
              active
                ? 'bg-foreground/10 font-medium text-foreground'
                : 'text-foreground/60 hover:bg-foreground/5 hover:text-foreground'
            }`}
          >
            {l.label}
          </button>
        );
      })}
    </div>
  );
}
