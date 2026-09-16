'use client';

// Implements: work-contracts/WC-096-conversational-customer-portal.md §4.1, §5
// Constitutional basis: C-001 (Human Override), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { MessageSquare, PanelRightClose, PanelRightOpen } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import type { PortalInteractionSurfaceV1 } from '@/lib/api/generated/models/PortalInteractionSurfaceV1';
import { ConversationExperience } from './ConversationExperience';
import { PortalGuideExperience } from './PortalGuideExperience';

export function routeContext(pathname: string): { surface: PortalInteractionSurfaceV1; label: string; action: string; relationshipId?: string } {
  const relationship = pathname.match(/^\/relationships\/([^/]+)/);
  if (relationship) return { surface: 'RELATIONSHIP', label: 'Professional conversation', action: 'Open conversation', relationshipId: decodeURIComponent(relationship[1]) };
  if (pathname.startsWith('/marketplace')) return { surface: 'MARKETPLACE', label: 'Marketplace', action: 'Ask about professionals' };
  if (pathname.startsWith('/professionals/mine')) return { surface: 'MY_AGENTS', label: 'My Agents', action: 'Discuss my agents' };
  if (pathname.startsWith('/alerts')) return { surface: 'ALERTS', label: 'Alerts', action: 'Review alerts' };
  if (pathname.startsWith('/settings')) return { surface: 'SETTINGS', label: 'Settings', action: 'Ask about settings' };
  if (pathname.startsWith('/profile')) return { surface: pathname.includes('billing') ? 'BILLING' : 'PROFILE', label: 'Account', action: 'Ask about my account' };
  return { surface: 'MY_AGENTS', label: 'Customer portal', action: 'Ask WAOOAW Guide' };
}

export function PersistentConversationDock({ locale = 'en-IN' }: { locale?: string }) {
  const pathname = usePathname();
  const context = routeContext(pathname);
  const [open, setOpen] = useState(false);
  const closeButton = useRef<HTMLButtonElement>(null);
  const openButton = useRef<HTMLButtonElement>(null);
  const lastOpener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setOpen(localStorage.getItem('waooaw:conversation-open') === 'true');
  }, []);
  useEffect(() => {
    if (!open) return;
    const close = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      localStorage.setItem('waooaw:conversation-open', 'false');
      (lastOpener.current ?? openButton.current)?.focus();
    };
    window.addEventListener('keydown', close);
    return () => window.removeEventListener('keydown', close);
  }, [open]);
  useEffect(() => {
    const openConversation = (event: Event) => {
      lastOpener.current = (event as CustomEvent<{ opener?: HTMLElement }>).detail?.opener ?? null;
      setDockOpen(true);
    };
    window.addEventListener('waooaw:open-conversation', openConversation);
    return () => window.removeEventListener('waooaw:open-conversation', openConversation);
  });

  function setDockOpen(value: boolean) {
    setOpen(value);
    localStorage.setItem('waooaw:conversation-open', String(value));
    if (value) requestAnimationFrame(() => closeButton.current?.focus());
  }

  return <><button aria-controls="persistent-conversation" aria-expanded={open} className="conversation-launcher" onClick={(event) => { lastOpener.current = event.currentTarget; setDockOpen(true); }} ref={openButton} type="button"><MessageSquare aria-hidden="true" size={19} /><span><small>{context.label}</small>{context.action}</span><PanelRightOpen aria-hidden="true" size={18} /></button><aside aria-label={context.relationshipId ? 'Professional conversation' : 'WAOOAW Guide'} className="persistent-conversation" data-open={open} id="persistent-conversation"><button aria-label="Close conversation" className="icon-command conversation-close" onClick={() => setDockOpen(false)} ref={closeButton} type="button"><PanelRightClose aria-hidden="true" size={20} /></button>{context.relationshipId ? <ConversationExperience key={context.relationshipId} relationshipId={context.relationshipId} /> : <PortalGuideExperience currentSurface={context.surface} locale={locale} />}</aside>{open ? <button aria-label="Close conversation overlay" className="conversation-scrim" onClick={() => setDockOpen(false)} type="button" /> : null}</>;
}

export function ConversationContextAction() {
  const context = routeContext(usePathname());
  return <button className="context-conversation-action" onClick={(event) => window.dispatchEvent(new CustomEvent('waooaw:open-conversation', { detail: { opener: event.currentTarget } }))} type="button"><MessageSquare aria-hidden="true" size={17} /><span>{context.action}</span></button>;
}