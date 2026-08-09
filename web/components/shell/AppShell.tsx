// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-001 (Human Override), C-059 (Implementation Traceability)

import { BriefcaseBusiness, Home, MessageSquare, Settings, ShieldCheck } from 'lucide-react';
import Link from 'next/link';
import type { ReactNode } from 'react';
import { EmergencyStop } from '@/components/constitutional/EmergencyStop';
import { Brand } from './Brand';
import { ExperienceControls } from './ExperienceControls';

type ShellVariant = 'public' | 'auth' | 'customer' | 'founder';

const publicLinks = [{ href: '/professionals', label: 'Professionals' }, { href: '/blogs', label: 'Blogs' }];
const customerLinks = [
  { href: '/home', label: 'Home', icon: Home },
  { href: '/professionals/mine', label: 'My WaooaW Experts', icon: BriefcaseBusiness },
  { href: '/settings', label: 'Settings', icon: Settings },
];

export function AppShell({ children, variant }: { children: ReactNode; variant: ShellVariant }) {
  const protectedShell = variant === 'customer' || variant === 'founder';
  return (
    <div className={`app-shell app-shell-${variant}`}>
      <a className="skip-link" href="#main-content">Skip to main content</a>
      <header className="top-bar">
        <Brand />
        {variant === 'public' ? <nav aria-label="Public navigation">{publicLinks.map((link) => <Link key={link.href} href={link.href}>{link.label}</Link>)}</nav> : null}
        <div className="top-actions">
          <ExperienceControls />
          {variant === 'public' ? <><Link href="/login">Log in</Link><Link className="primary-link" href="/register">Register</Link></> : null}
          {variant === 'founder' ? <span className="role-label"><ShieldCheck aria-hidden="true" size={17} /> Founder</span> : null}
        </div>
      </header>
      {protectedShell ? (
        <aside className="side-navigation">
          <nav aria-label={variant === 'founder' ? 'Founder navigation' : 'Customer navigation'}>
            {(variant === 'founder' ? [{ href: '/founder', label: 'Founder home', icon: ShieldCheck }] : customerLinks).map(({ href, label, icon: Icon }) => (
              <Link key={href} href={href}><Icon aria-hidden="true" size={20} /><span>{label}</span></Link>
            ))}
          </nav>
        </aside>
      ) : null}
      <main className="main-content" id="main-content" tabIndex={-1}>{children}</main>
      {protectedShell ? <EmergencyStop contractId={null} activeSessionIds={[]} /> : null}
      {variant === 'customer' ? (
        <nav className="bottom-navigation" aria-label="Customer mobile navigation">
          <Link href="/home"><MessageSquare aria-hidden="true" size={21} /><span>Conversation</span></Link>
          <Link href="/home?view=plan"><Home aria-hidden="true" size={21} /><span>Plan</span></Link>
          <Link href="/home?view=work"><BriefcaseBusiness aria-hidden="true" size={21} /><span>Work</span></Link>
          <Link href="/professionals/mine"><Settings aria-hidden="true" size={21} /><span>WaooaW Experts</span></Link>
        </nav>
      ) : null}
    </div>
  );
}