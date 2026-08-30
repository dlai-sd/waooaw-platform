// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-001 (Human Override), C-059 (Implementation Traceability)

import { BriefcaseBusiness, Home, MessageSquare, Settings, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { AccountSwitchCommand, SignOutCommand } from '@/components/auth/SignOutCommand';
import type { Messages } from '@/lib/i18n';
import { AppShell } from './AppShell';
import { RouteAwareEmergencyStop } from './RouteAwareEmergencyStop';

export interface StopContext {
  contractId: string;
  activeSessionIds: string[];
}

type ProtectedVariant = 'customer' | 'founder';

export function ProtectedAppShell({ children, messages, stopContext, variant }: {
  children: ReactNode;
  messages: Messages;
  stopContext?: StopContext;
  variant: ProtectedVariant;
}) {
  const customerLinks = [
    { href: '/home', label: messages.home, icon: Home },
    { href: '/professionals/mine', label: messages.myExperts, icon: BriefcaseBusiness },
    { href: '/settings', label: messages.settings, icon: Settings },
  ];
  const links = variant === 'founder'
    ? [{ href: '/founder', label: messages.founderHome, icon: ShieldCheck }]
    : customerLinks;

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
        <a href="/founder"><ShieldCheck aria-hidden="true" size={21} /><span>{messages.founderHome}</span></a>
      ) : (
        <>
          <a href="/home"><MessageSquare aria-hidden="true" size={21} /><span>{messages.conversation}</span></a>
          <a href="/home?view=plan"><Home aria-hidden="true" size={21} /><span>{messages.plan}</span></a>
          <a href="/home?view=work"><BriefcaseBusiness aria-hidden="true" size={21} /><span>{messages.work}</span></a>
          <Link href="/professionals/mine"><Settings aria-hidden="true" size={21} /><span>{messages.waooawExperts}</span></Link>
        </>
      )}
    </nav>
  );

  return (
    <AppShell
      bottomNavigation={bottomNavigation}
      headerStatus={<>{variant === 'founder' ? <span className="role-label"><ShieldCheck aria-hidden="true" size={17} /> {messages.founder}</span> : null}<AccountSwitchCommand label="Switch account" /><SignOutCommand label="Sign out" /></>}
      messages={messages}
      sideNavigation={sideNavigation}
      stopControl={<RouteAwareEmergencyStop stopContext={stopContext} />}
      variant={variant}
    >
      {children}
    </AppShell>
  );
}
