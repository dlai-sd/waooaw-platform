'use client';

// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md §5.4 Authenticated Application Shell
// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C2-05
// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R006
// Implements: work-contracts/WC-149-paid-provider-consumption-and-customer-account-connection.md WC149-R010
// Constitutional basis: C-001 (Human Override), C-059 (Implementation Traceability)

import {
  Activity,
  BadgeCheck,
  Bell,
  Bot,
  ChevronLeft,
  ChevronRight,
  CircleUserRound,
  CreditCard,
  KeyRound,
  Menu,
  Settings,
  ShieldCheck,
  SlidersHorizontal,
  Store,
  Tag,
  UserCheck,
  UserRound,
  Vault,
  type LucideIcon,
} from 'lucide-react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AccountSwitchCommand, SignOutCommand } from '@/components/auth/SignOutCommand';
import { SessionValidityGuard } from '@/components/auth/SessionValidityGuard';
import { PersistentConversationDock } from '@/components/conversation/PersistentConversationDock';
import type { IdentitySession } from '@/lib/api/generated/models/IdentitySession';
import type { WorkspaceLayoutPreferencesV1 } from '@/lib/api/generated/models/WorkspaceLayoutPreferencesV1';
import type { Messages } from '@/lib/i18n';
import { portalMessages } from '@/lib/portal-i18n';
import type { SupportedLocale } from '@/lib/preferences';
import { recordAuthTransition } from '@/lib/auth-transition';
import { founderMenu, operationsMenu, platformMenu, type MenuIcon, type MenuLink } from '@/lib/navigation-model';
import { AppShell } from './AppShell';
import { Brand } from './Brand';
import { ExperienceControls } from './ExperienceControls';
import { RouteAwareEmergencyStop } from './RouteAwareEmergencyStop';

export interface StopContext {
  contractId: string;
  activeSessionIds: string[];
}

type ProtectedVariant = 'customer' | 'founder';

const menuIcons: Record<MenuIcon, LucideIcon> = {
  agents: Bot,
  marketplace: Store,
  alerts: Bell,
  settings: Settings,
  operations: Activity,
  vault: Vault,
  pricing: Tag,
  providers: KeyRound,
  'agent-operation': SlidersHorizontal,
  professionals: BadgeCheck,
  access: UserCheck,
  founder: ShieldCheck,
};

export function ProtectedAppShell({
  children,
  identitySession,
  locale = 'en',
  messages,
  showAccess = false,
  showKeyVaultAdmin = false,
  showOperations = false,
  showPricingAdmin = false,
  showProviderAdmin = false,
  stopContext,
  variant,
  workspaceLayout,
}: {
  children: ReactNode;
  identitySession?: IdentitySession;
  locale?: SupportedLocale;
  messages: Messages;
  showAccess?: boolean;
  showKeyVaultAdmin?: boolean;
  showOperations?: boolean;
  showPricingAdmin?: boolean;
  showProviderAdmin?: boolean;
  stopContext?: StopContext;
  variant: ProtectedVariant;
  workspaceLayout?: WorkspaceLayoutPreferencesV1;
}) {
  const pathname = usePathname();
  const [navigationExpanded, setNavigationExpanded] = useState(workspaceLayout?.navigationVisibility === 'VISIBLE');
  const navigationToggle = useRef<HTMLButtonElement>(null);
  const accountDrawer = useRef<HTMLDetailsElement>(null);
  const accountToggle = useRef<HTMLElement>(null);
  const portal = portalMessages[locale];
  const registeredCustomer = identitySession !== undefined;
  // One global menu for every customer and agent; staff tools sit in their own group and never in the customer list.
  const links: MenuLink[] =
    variant === 'founder'
      ? founderMenu(messages.founderHome)
      : platformMenu({
          myAgents: portal.myAgents,
          marketplace: portal.marketplace,
          alerts: portal.alerts,
          settings: messages.settings,
        });
  // The Founder holds every staff tool, so the Founder menu reaches all of them; Staff access already sits in the main list.
  const operationsLinks: MenuLink[] =
    variant === 'founder'
      ? operationsMenu({
          showKeyVaultAdmin: true,
          showOperations: true,
          showPricingAdmin: true,
          showProviderAdmin: true,
        })
      : operationsMenu({ showAccess, showKeyVaultAdmin, showOperations, showPricingAdmin, showProviderAdmin });
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
          {showAccess ? (
            <Link href="/access">
              <UserCheck aria-hidden="true" size={18} />
              Staff access
            </Link>
          ) : null}
          <AccountSwitchCommand label="Switch account" />
          <SignOutCommand label="Sign out" />
        </div>
      </details>
    ) : null;

  function renderLinks(items: MenuLink[]) {
    return items.map(({ id, href, label, icon }) => {
      const Icon = menuIcons[icon];
      return (
        <Link
          aria-current={pathname === href || pathname.startsWith(`${href}/`) ? 'page' : undefined}
          key={id}
          href={href}
          onClick={() => {
            if (window.matchMedia('(max-width: 899px)').matches) setNavigationExpanded(false);
          }}
          title={navigationExpanded ? undefined : label}
        >
          <Icon aria-hidden="true" size={20} />
          <span>{label}</span>
        </Link>
      );
    });
  }

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
        {renderLinks(links)}
      </nav>
      {operationsLinks.length > 0 ? (
        <nav aria-label="Operations" className="operations-navigation">
          <p className="section-label">Operations</p>
          {renderLinks(operationsLinks)}
        </nav>
      ) : null}
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
          <button
            aria-controls="customer-navigation"
            aria-expanded={navigationExpanded}
            className="bottom-menu-command"
            onClick={toggleNavigation}
            type="button"
          >
            <Menu aria-hidden="true" size={21} />
            <span>Menu</span>
          </button>
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
          variant === 'customer' && registeredCustomer ? (
            <PersistentConversationDock
              conversationWidthPercent={workspaceLayout?.conversationWidthPercent}
              locale={locale}
              reduceMotion={workspaceLayout?.reduceMotion}
            />
          ) : null
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
