'use client';

// Implements: architecture/reference/ux/hybrid-visual-system-contract.md §Global Chrome
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import { Languages, Moon, Sun } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { resolveLocale, resolveTheme, supportedLocales, type SupportedLocale, type ThemePreference } from '@/lib/preferences';

const localeNames: Record<SupportedLocale, string> = {
  en: 'English', hi: 'हिन्दी', mr: 'मराठी', ta: 'தமிழ்', te: 'తెలుగు', kn: 'ಕನ್ನಡ',
  gu: 'ગુજરાતી', bn: 'বাংলা', ml: 'മലയാളം', pa: 'ਪੰਜਾਬੀ', ur: 'اردو',
};

function setPreference(name: string, value: string) {
  document.cookie = `${name}=${value}; Path=/; Max-Age=31536000; SameSite=Lax`;
}

export function ExperienceControls() {
  const router = useRouter();
  const [locale, setLocale] = useState<SupportedLocale>('en');
  const [theme, setTheme] = useState<ThemePreference>('system');

  useEffect(() => {
    setLocale(resolveLocale(document.documentElement.lang));
    setTheme(resolveTheme(document.documentElement.dataset.theme));
  }, []);

  function changeLocale(nextLocale: SupportedLocale) {
    setLocale(nextLocale);
    setPreference('waooaw-locale', nextLocale);
    router.refresh();
  }

  function toggleTheme() {
    const nextTheme: ThemePreference = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    setPreference('waooaw-theme', nextTheme);
    document.documentElement.dataset.theme = nextTheme;
  }

  return (
    <div className="experience-controls">
      <label className="select-control">
        <Languages aria-hidden="true" size={18} />
        <span className="visually-hidden">Language</span>
        <select aria-label="Language" value={locale} onChange={(event) => changeLocale(event.target.value as SupportedLocale)}>
          {supportedLocales.map((option) => <option key={option} value={option}>{localeNames[option]}</option>)}
        </select>
      </label>
      <button className="icon-command" type="button" onClick={toggleTheme} aria-label={`Use ${theme === 'dark' ? 'light' : 'dark'} theme`}>
        {theme === 'dark' ? <Sun aria-hidden="true" size={19} /> : <Moon aria-hidden="true" size={19} />}
      </button>
    </div>
  );
}