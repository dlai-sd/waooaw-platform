// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-001 (Human Override), C-059 (Implementation Traceability)

import { Bell, Bot, CircleUserRound, CreditCard, Settings, ShieldCheck, Store, UserRound } from 'lucide-react';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { AccountSwitchCommand, SignOutCommand } from '@/components/auth/SignOutCommand';
import type { IdentitySession } from '@/lib/api/generated/models/IdentitySession';
import type { Messages } from '@/lib/i18n';
import { portalMessages } from '@/lib/portal-i18n';
import type { SupportedLocale } from '@/lib/preferences';
import { AppShell } from './AppShell';
import { RouteAwareEmergencyStop } from './RouteAwareEmergencyStop';

export interface StopContext {
  contractId: string;
  activeSessionIds: string[];
}

type ProtectedVariant = 'customer' | 'founder';

export function ProtectedAppShell({ children, identitySession, locale = 'en', messages, stopContext, variant }: {
  children: ReactNode;
  identitySession?: IdentitySession;
  locale?: SupportedLocale;
  messages: Messages;
  stopContext?: StopContext;
  variant: ProtectedVariant;
}) {
  const portal = portalMessages[locale];
  const customerLinks = [
    { href: '/home', label: portal.myAgents, icon: Bot },
    { href: '/marketplace', label: portal.marketplace, icon: Store },
    { href: '/alerts', label: portal.alerts, icon: Bell },
    { href: '/settings', label: messages.settings, icon: Settings },
  ];
  const links = variant === 'founder'
    ? [{ href: '/founder', label: messages.founderHome, icon: ShieldCheck }]
    : customerLinks;
  const accountDrawer = variant === 'customer' ? <details className="account-drawer"><summary className="icon-command" aria-label="Account"><CircleUserRound aria-hidden="true" size={20} /></summary><div><p className="section-label">Account</p><Link href="/profile"><UserRound aria-hidden="true" size={18} />Profile</Link><Link href="/profile#billing"><CreditCard aria-hidden="true" size={18} />Billing</Link><Link href="/settings"><Settings aria-hidden="true" size={18} />Settings</Link><AccountSwitchCommand label="Switch account" /><SignOutCommand label="Sign out" /></div></details> : null;

  const sideNavigation = (
    <aside className="side-navigation">
      <nav aria-label={variant === 'founder' ? messages.founderNavigation : messages.customerNavigation}>
        {links.map(({ href, label, icon: Icon }) => (
          <a key={href} href={href}><Icon aria-hidden="true" size={20} /><span>{label}</span></a>
        ))}
      </nav>
    </aside>
  );
  const bottomNavigation = (
    <nav className={`bottom-navigation bottom-navigation-${variant}`} aria-label={variant === 'founder' ? messages.founderNavigation : messages.customerMobileNavigation}>
      {variant === 'founder' ? (
        <Link href="/founder"><ShieldCheck aria-hidden="true" size={21} /><span>{messages.founderHome}</span></Link>
      ) : (
        <>
          <Link href="/home"><Bot aria-hidden="true" size={21} /><span>{portal.myAgents}</span></Link>
          <Link href="/marketplace"><Store aria-hidden="true" size={21} /><span>{portal.marketplace}</span></Link>
          <Link href="/alerts"><Bell aria-hidden="true" size={21} /><span>{portal.alerts}</span></Link>
        </>
      )}
    </nav>
  );

  return (
    <AppShell
      bottomNavigation={bottomNavigation}
      headerStatus={<>{variant === 'founder' ? <span className="role-label"><ShieldCheck aria-hidden="true" size={17} /> {messages.founder}</span> : null}{identitySession ? <span className="portal-assurance"><ShieldCheck aria-hidden="true" size={16} />{portal.verified} · {identitySession.assuranceLevel}</span> : null}{accountDrawer}</>}
      messages={messages}
      sideNavigation={sideNavigation}
      stopControl={<RouteAwareEmergencyStop stopContext={stopContext} />}
      variant={variant}
    >
      {children}
    </AppShell>
  );
}
