import { LANGS, setLang, useLang, useT } from '../lib/i18n';
import { Segmented } from './Segmented';

/* Sits next to the theme control — the header is where people already look
 * for display preferences. */
export function LangSwitch() {
  const lang = useLang();
  const t = useT();
  return (
    <Segmented
      label={t('app.language')}
      value={lang}
      onChange={setLang}
      options={LANGS.map((l) => ({ id: l.id, label: l.label }))}
    />
  );
}
