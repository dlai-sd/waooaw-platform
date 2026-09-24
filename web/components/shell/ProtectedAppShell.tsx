'use client';

// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md §5.4 Authenticated Application Shell
// Constitutional basis: C-001 (Human Override), C-059 (Implementation Traceability)

import {
  Bell,
  Bot,
  ChevronLeft,
  ChevronRight,
  CircleUserRound,
  CreditCard,
  Settings,
  ShieldCheck,
  Store,
  UserRound,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AccountSwitchCommand, SignOutCommand } from '@/components/auth/SignOutCommand';
import { SessionValidityGuard } from '@/components/auth/SessionValidityGuard';
import { PersistentConversationDock } from '@/components/conversation/PersistentConversationDock';
import type { IdentitySession } from '@/lib/api/generated/models/IdentitySession';
import type { Messages } from '@/lib/i18n';
import { portalMessages } from '@/lib/portal-i18n';
import type { SupportedLocale } from '@/lib/preferences';
import { recordAuthTransition } from '@/lib/auth-transition';
import { AppShell } from './AppShell';
import { Brand } from './Brand';
import { ExperienceControls } from './ExperienceControls';
import { RouteAwareEmergencyStop } from './RouteAwareEmergencyStop';

export interface StopContext {
  contractId: string;
  activeSessionIds: string[];
}

type ProtectedVariant = 'customer' | 'founder';

export function ProtectedAppShell({
  children,
  identitySession,
  locale = 'en',
  messages,
  stopContext,
  variant,
}: {
  children: ReactNode;
  identitySession?: IdentitySession;
  locale?: SupportedLocale;
  messages: Messages;
  stopContext?: StopContext;
  variant: ProtectedVariant;
}) {
  const pathname = usePathname();
  const [navigationExpanded, setNavigationExpanded] = useState(false);
  const navigationToggle = useRef<HTMLButtonElement>(null);
  const accountDrawer = useRef<HTMLDetailsElement>(null);
  const accountToggle = useRef<HTMLElement>(null);
  const portal = portalMessages[locale];
  const registeredCustomer = identitySession !== undefined;
  const customerLinks = [
    { href: '/professionals/mine', label: portal.myAgents, icon: Bot },
    { href: '/marketplace', label: portal.marketplace, icon: Store },
    { href: '/alerts', label: portal.alerts, icon: Bell },
    { href: '/settings', label: messages.settings, icon: Settings },
  ];
  const links =
    variant === 'founder' ? [{ href: '/founder', label: messages.founderHome, icon: ShieldCheck }] : customerLinks;
  useEffect(() => {
    setNavigationExpanded(localStorage.getItem('waooaw:navigation-expanded') === 'true');
  }, []);
  useEffect(() => {
    if (identitySession) recordAuthTransition('SESSION_RESOLVED');
  }, [identitySession]);
  useEffect(() => {
    if (!navigationExpanded) return;
    function collapse(event: KeyboardEvent) {
      if (event.key !== 'Escape') return;
      setNavigationExpanded(false);
      localStorage.setItem('waooaw:navigation-expanded', 'false');
      navigationToggle.current?.focus();
    }
    window.addEventListener('keydown', collapse);
    return () => window.removeEventListener('keydown', collapse);
  }, [navigationExpanded]);
  useEffect(() => {
    function dismissAccountDrawer(event: PointerEvent) {
      const drawer = accountDrawer.current;
      if (drawer?.open && event.target instanceof Node && !drawer.contains(event.target)) drawer.open = false;
    }
    function closeAccountDrawer(event: KeyboardEvent) {
      const drawer = accountDrawer.current;
      if (event.key !== 'Escape' || !drawer?.open) return;
      drawer.open = false;
      accountToggle.current?.focus();
    }
    document.addEventListener('pointerdown', dismissAccountDrawer);
    window.addEventListener('keydown', closeAccountDrawer);
    return () => {
      document.removeEventListener('pointerdown', dismissAccountDrawer);
      window.removeEventListener('keydown', closeAccountDrawer);
    };
  }, []);

  function toggleNavigation() {
    setNavigationExpanded((expanded) => {
      localStorage.setItem('waooaw:navigation-expanded', String(!expanded));
      return !expanded;
    });
  }
  const accountControl =
    variant === 'customer' ? (
      <details className="account-drawer" ref={accountDrawer}>
        <summary className="icon-command" aria-label="Account" ref={accountToggle}>
          <CircleUserRound aria-hidden="true" size={20} />
        </summary>
        <div>
          <p className="section-label">Account</p>
          {identitySession ? (
            <p className="account-assurance">
              <ShieldCheck aria-hidden="true" size={17} />
              Account security: {portal.verified}
            </p>
          ) : null}
          <Link href="/profile">
            <UserRound aria-hidden="true" size={18} />
            Profile
          </Link>
          <Link href="/profile#billing">
            <CreditCard aria-hidden="true" size={18} />
            Billing
          </Link>
          <Link href="/settings">
            <Settings aria-hidden="true" size={18} />
            Settings
          </Link>
          <AccountSwitchCommand label="Switch account" />
          <SignOutCommand label="Sign out" />
        </div>
      </details>
    ) : null;

  const sideNavigation = (
    <aside className="side-navigation" data-expanded={navigationExpanded} id="customer-navigation">
      <div className="rail-brand">
        <Brand compact={!navigationExpanded} />
        <button
          aria-controls="customer-navigation"
          aria-expanded={navigationExpanded}
          aria-label={navigationExpanded ? 'Collapse navigation' : 'Expand navigation'}
          className="icon-command navigation-toggle"
          onClick={toggleNavigation}
          ref={navigationToggle}
          type="button"
        >
          {navigationExpanded ? (
            <ChevronLeft aria-hidden="true" size={20} />
          ) : (
            <ChevronRight aria-hidden="true" size={20} />
          )}
        </button>
      </div>
      <nav aria-label={variant === 'founder' ? messages.founderNavigation : messages.customerNavigation}>
        {links.map(({ href, label, icon: Icon }) => (
          <Link
            aria-current={pathname === href || pathname.startsWith(`${href}/`) ? 'page' : undefined}
            key={href}
            href={href}
            onClick={() => {
              if (window.matchMedia('(max-width: 899px)').matches) setNavigationExpanded(false);
            }}
            title={navigationExpanded ? undefined : label}
          >
            <Icon aria-hidden="true" size={20} />
            <span>{label}</span>
          </Link>
        ))}
      </nav>
      <ExperienceControls messages={messages} />
    </aside>
  );
  const bottomNavigation = (
    <nav
      className={`bottom-navigation bottom-navigation-${variant}`}
      aria-label={variant === 'founder' ? messages.founderNavigation : messages.customerMobileNavigation}
    >
      {variant === 'founder' ? (
        <Link href="/founder">
          <ShieldCheck aria-hidden="true" size={21} />
          <span>{messages.founderHome}</span>
        </Link>
      ) : (
        <>
          <Link href="/professionals/mine">
            <Bot aria-hidden="true" size={21} />
            <span>{portal.myAgents}</span>
          </Link>
          <Link href="/marketplace">
            <Store aria-hidden="true" size={21} />
            <span>{portal.marketplace}</span>
          </Link>
          <Link href="/alerts">
            <Bell aria-hidden="true" size={21} />
            <span>{portal.alerts}</span>
          </Link>
        </>
      )}
    </nav>
  );

  return (
    <>
      {identitySession ? <SessionValidityGuard /> : null}
      <AppShell
        applicationControls={
          <div className="application-controls">
            {variant === 'founder' ? (
              <span className="role-label">
                <ShieldCheck aria-hidden="true" size={17} /> {messages.founder}
              </span>
            ) : null}
            {accountControl}
          </div>
        }
        bottomNavigation={bottomNavigation}
        conversationWorkspace={
          variant === 'customer' && registeredCustomer ? <PersistentConversationDock locale={locale} /> : null
        }
        messages={messages}
        sideNavigation={sideNavigation}
        stopControl={<RouteAwareEmergencyStop stopContext={stopContext} />}
        variant={variant}
      >
        {children}
      </AppShell>
    </>
  );
}
