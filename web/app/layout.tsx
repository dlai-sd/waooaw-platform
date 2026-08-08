import type { Metadata, Viewport } from 'next';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: 'WAOOAW Employment Workspace',
  description: 'Employ and govern WAOOAW digital professionals.',
  manifest: '/manifest.webmanifest',
};

export const viewport: Viewport = { themeColor: '#17334e' };

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}