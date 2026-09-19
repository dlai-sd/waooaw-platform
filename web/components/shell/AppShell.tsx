// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md §5.4 Authenticated Application Shell
// Constitutional basis: C-001 (Human Override), C-059 (Implementation Traceability)

import type { ReactNode } from 'react';
import Link from 'next/link';
import { AnnouncementBar } from '@/components/public/AnnouncementBar';
import { PublicFooter } from '@/components/public/PublicFooter';
import { siteConfig } from '@/config/site';
import type { Messages } from '@/lib/i18n';
import { Brand } from './Brand';
import { ExperienceControls } from './ExperienceControls';
import { HeaderScrollState } from './HeaderScrollState';

type ShellVariant = 'public' | 'auth' | 'customer' | 'founder';

export function AppShell({
  applicationControls,
  bottomNavigation,
  children,
  conversationWorkspace,
  headerStatus,
  messages,
  sideNavigation,
  stopControl,
  variant,
}: {
  applicationControls?: ReactNode;
  bottomNavigation?: ReactNode;
  children: ReactNode;
  conversationWorkspace?: ReactNode;
  headerStatus?: ReactNode;
  messages: Messages;
  sideNavigation?: ReactNode;
  stopControl?: ReactNode;
  variant: ShellVariant;
}) {
  const publicLinks = siteConfig.publicNavigation;
  const hasTopBar = variant === 'public' || variant === 'auth';
  return (
    <>
      {variant === 'public' ? <AnnouncementBar announcement={siteConfig.announcement} /> : null}
      <div className={`app-shell app-shell-${variant}`}>
        <a className="skip-link" href="#main-content">
          {messages.skipToContent}
        </a>
        {hasTopBar ? (
          <header className="top-bar">
            {variant === 'public' ? <HeaderScrollState /> : null}
            <Brand />
            {variant === 'public' ? (
              <nav aria-label={messages.publicNavigation}>
                {publicLinks.map((link) => (
                  <a key={link.href} href={link.href}>
                    {link.label}
                  </a>
                ))}
              </nav>
            ) : null}
            <div className="top-actions">
              <ExperienceControls messages={messages} />
              {variant === 'public' ? (
                <>
                  <Link href="/login">{messages.login}</Link>
                  <Link className="primary-link" href="/register">
                    {messages.register}
                  </Link>
                </>
              ) : null}
              {headerStatus}
            </div>
          </header>
        ) : null}
        {sideNavigation}
        {applicationControls}
        <main className="main-content" id="main-content" tabIndex={-1}>
          {children}
        </main>
        {conversationWorkspace}
        {variant === 'public' ? <PublicFooter /> : null}
        {stopControl}
        {bottomNavigation}
      </div>
    </>
  );
}
