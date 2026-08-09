import type { Metadata, Viewport } from 'next';
import { Noto_Nastaliq_Urdu, Noto_Sans } from 'next/font/google';
import { cookies } from 'next/headers';
import type { ReactNode } from 'react';
import { OfflineNotice } from '@/components/shell/OfflineNotice';
import { directionForLocale, resolveLocale, resolveTheme } from '@/lib/preferences';
import './globals.css';

// Implements: architecture/reference/ux/hybrid-application-shell.md §Server and Client Rendering Rules
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

const notoSans = Noto_Sans({ subsets: ['latin'], variable: '--font-sans', display: 'swap' });
const notoUrdu = Noto_Nastaliq_Urdu({ subsets: ['arabic'], variable: '--font-urdu', display: 'swap', preload: false });

export const metadata: Metadata = {
  title: 'WAOOAW Employment Workspace',
  description: 'Employ and govern WAOOAW digital professionals.',
  manifest: '/manifest.webmanifest',
};

export const viewport: Viewport = { themeColor: '#1e3352', width: 'device-width', initialScale: 1 };

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const cookieStore = cookies();
  const locale = resolveLocale(cookieStore.get('waooaw-locale')?.value);
  const theme = resolveTheme(cookieStore.get('waooaw-theme')?.value);

  return (
    <html
      className={`${notoSans.variable} ${notoUrdu.variable}`}
      data-theme={theme}
      dir={directionForLocale(locale)}
      lang={locale}
      suppressHydrationWarning
    >
      <body>
        <OfflineNotice />
        {children}
      </body>
    </html>
  );
}