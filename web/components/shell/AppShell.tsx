// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-001 (Human Override), C-059 (Implementation Traceability)

import type { ReactNode } from 'react';
import type { Messages } from '@/lib/i18n';
import { Brand } from './Brand';
import { ExperienceControls } from './ExperienceControls';

type ShellVariant = 'public' | 'auth' | 'customer' | 'founder';

export function AppShell({ bottomNavigation, children, headerStatus, messages, sideNavigation, stopControl, variant }: {
  bottomNavigation?: ReactNode;
  children: ReactNode;
  headerStatus?: ReactNode;
  messages: Messages;
  sideNavigation?: ReactNode;
  stopControl?: ReactNode;
  variant: ShellVariant;
}) {
  const publicLinks = [{ href: '/professionals', label: messages.professionals }, { href: '/blogs', label: messages.blogs }];
  return (
    <div className={`app-shell app-shell-${variant}`}>
      <a className="skip-link" href="#main-content">{messages.skipToContent}</a>
      <header className="top-bar">
        <Brand />
        {variant === 'public' ? <nav aria-label={messages.publicNavigation}>{publicLinks.map((link) => <a key={link.href} href={link.href}>{link.label}</a>)}</nav> : null}
        <div className="top-actions">
          <ExperienceControls messages={messages} />
          {variant === 'public' ? <><a href="/login">{messages.login}</a><a className="primary-link" href="/register">{messages.register}</a></> : null}
          {headerStatus}
        </div>
      </header>
      {sideNavigation}
      <main className="main-content" id="main-content" tabIndex={-1}>{children}</main>
      {stopControl}
      {bottomNavigation}
    </div>
  );
}