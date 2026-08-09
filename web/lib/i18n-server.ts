// Implements: architecture/reference/ux/hybrid-application-shell.md §Server and Client Rendering Rules
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import { cookies } from 'next/headers';
import { getMessages } from './i18n';
import { resolveLocale } from './preferences';

export function getRequestI18n() {
  const locale = resolveLocale(cookies().get('waooaw-locale')?.value);
  return { locale, messages: getMessages(locale) };
}