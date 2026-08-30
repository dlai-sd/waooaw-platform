import type { Metadata, Viewport } from 'next';
import {
  Noto_Nastaliq_Urdu,
  Noto_Sans,
  Noto_Sans_Bengali,
  Noto_Sans_Devanagari,
  Noto_Sans_Gujarati,
  Noto_Sans_Gurmukhi,
  Noto_Sans_Kannada,
  Noto_Sans_Malayalam,
  Noto_Sans_Tamil,
  Noto_Sans_Telugu,
} from 'next/font/google';
import { cookies } from 'next/headers';
import type { ReactNode } from 'react';
import '@/config/public-config';
import { siteConfig } from '@/config/site';
import { OfflineNotice } from '@/components/shell/OfflineNotice';
import { directionForLocale, resolveLocale, resolveTheme } from '@/lib/preferences';
import './globals.css';

// Implements: architecture/reference/ux/hybrid-application-shell.md §Server and Client Rendering Rules
// Constitutional basis: C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

const notoSans = Noto_Sans({ subsets: ['latin'], variable: '--font-sans', display: 'swap' });
const notoUrdu = Noto_Nastaliq_Urdu({ subsets: ['arabic'], variable: '--font-urdu', display: 'swap', preload: false });
const notoDevanagari = Noto_Sans_Devanagari({ subsets: ['devanagari'], variable: '--font-devanagari', display: 'swap', preload: false });
const notoTamil = Noto_Sans_Tamil({ subsets: ['tamil'], variable: '--font-tamil', display: 'swap', preload: false });
const notoTelugu = Noto_Sans_Telugu({ subsets: ['telugu'], variable: '--font-telugu', display: 'swap', preload: false });
const notoKannada = Noto_Sans_Kannada({ subsets: ['kannada'], variable: '--font-kannada', display: 'swap', preload: false });
const notoGujarati = Noto_Sans_Gujarati({ subsets: ['gujarati'], variable: '--font-gujarati', display: 'swap', preload: false });
const notoBengali = Noto_Sans_Bengali({ subsets: ['bengali'], variable: '--font-bengali', display: 'swap', preload: false });
const notoMalayalam = Noto_Sans_Malayalam({ subsets: ['malayalam'], variable: '--font-malayalam', display: 'swap', preload: false });
const notoGurmukhi = Noto_Sans_Gurmukhi({ subsets: ['gurmukhi'], variable: '--font-gurmukhi', display: 'swap', preload: false });

const fontVariables = [notoSans, notoUrdu, notoDevanagari, notoTamil, notoTelugu, notoKannada, notoGujarati, notoBengali, notoMalayalam, notoGurmukhi]
  .map((font) => font.variable)
  .join(' ');

export const metadata: Metadata = {
  metadataBase: new URL(siteConfig.canonicalOrigin),
  title: { default: 'WAOOAW | Governed digital professionals', template: '%s' },
  description: 'Employ a governed digital professional with visible scope, reviewable work, and control that remains yours.',
  manifest: '/manifest.webmanifest',
  alternates: { canonical: '/' },
  openGraph: { title: 'WAOOAW', description: 'Governed digital professionals for practical work.', url: '/', siteName: 'WAOOAW', type: 'website' },
};

export const viewport: Viewport = { themeColor: '#1e3352', width: 'device-width', initialScale: 1 };

export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const cookieStore = await cookies();
  const locale = resolveLocale(cookieStore.get('waooaw-locale')?.value);
  const theme = resolveTheme(cookieStore.get('waooaw-theme')?.value);

  return (
    <html
      className={fontVariables}
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