'use client';

// Implements: work-contracts/WC-099-demo-customer-journey-and-application-shell-remediation.md §5.5 Guide Workspace And Configuration
// Constitutional basis: C-001 (Human Override), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { MessageSquare, PanelRightClose, PanelRightOpen } from 'lucide-react';
import { usePathname } from 'next/navigation';
import { useEffect, useRef, useState, type CSSProperties, type MouseEvent as ReactMouseEvent, type PointerEvent as ReactPointerEvent } from 'react';
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
  const [width, setWidth] = useState(400);
  const dragStart = useRef<{ pointerX: number; width: number }>();
  const closeButton = useRef<HTMLButtonElement>(null);
  const dock = useRef<HTMLElement>(null);
  const openButton = useRef<HTMLButtonElement>(null);
  const lastOpener = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setOpen(localStorage.getItem('waooaw:conversation-open') === 'true');
    const storedWidth = Number(localStorage.getItem('waooaw:conversation-width'));
    if (Number.isFinite(storedWidth) && storedWidth >= 320 && storedWidth <= 560) setWidth(storedWidth);
  }, []);
  useEffect(() => {
    if (!open) return;
    const handleSheetKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
        localStorage.setItem('waooaw:conversation-open', 'false');
        (lastOpener.current ?? openButton.current)?.focus();
        return;
      }
      if (event.key !== 'Tab' || !window.matchMedia('(max-width: 899px)').matches) return;
      const commands = [...(dock.current?.querySelectorAll<HTMLElement>('a[href], button:not([disabled]), textarea:not([disabled]), [tabindex="0"]') ?? [])]
        .filter((command) => {
          const style = getComputedStyle(command);
          return style.display !== 'none' && style.visibility !== 'hidden';
        });
      if (!commands.length) return;
      const first = commands[0];
      const last = commands[commands.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        last.focus();
        event.preventDefault();
      } else if (!event.shiftKey && document.activeElement === last) {
        first.focus();
        event.preventDefault();
      }
    };
    window.addEventListener('keydown', handleSheetKey);
    return () => window.removeEventListener('keydown', handleSheetKey);
  }, [open]);
  useEffect(() => {
    const openConversation = (event: Event) => {
      lastOpener.current = (event as CustomEvent<{ opener?: HTMLElement }>).detail?.opener ?? null;
      setDockOpen(true);
    };
    window.addEventListener('waooaw:open-conversation', openConversation);
    return () => window.removeEventListener('waooaw:open-conversation', openConversation);
  });
  useEffect(() => {
    function continueWindowResize(event: PointerEvent) {
      if (!dragStart.current) return;
      const direction = document.documentElement.dir === 'rtl' ? -1 : 1;
      setBoundedWidth(dragStart.current.width + (dragStart.current.pointerX - event.clientX) * direction);
    }
    function stopWindowResize() {
      dragStart.current = undefined;
    }
    function continueMouseResize(event: MouseEvent) {
      if (!dragStart.current) return;
      const direction = document.documentElement.dir === 'rtl' ? -1 : 1;
      setBoundedWidth(dragStart.current.width + (dragStart.current.pointerX - event.clientX) * direction);
    }
    window.addEventListener('pointermove', continueWindowResize);
    window.addEventListener('pointerup', stopWindowResize);
    window.addEventListener('pointercancel', stopWindowResize);
    window.addEventListener('mousemove', continueMouseResize);
    window.addEventListener('mouseup', stopWindowResize);
    return () => {
      window.removeEventListener('pointermove', continueWindowResize);
      window.removeEventListener('pointerup', stopWindowResize);
      window.removeEventListener('pointercancel', stopWindowResize);
      window.removeEventListener('mousemove', continueMouseResize);
      window.removeEventListener('mouseup', stopWindowResize);
    };
  });

  function setDockOpen(value: boolean) {
    setOpen(value);
    localStorage.setItem('waooaw:conversation-open', String(value));
    if (value) requestAnimationFrame(() => closeButton.current?.focus());
  }

  function setBoundedWidth(nextWidth: number) {
    const boundedWidth = Math.min(560, Math.max(320, nextWidth));
    setWidth(boundedWidth);
    localStorage.setItem('waooaw:conversation-width', String(boundedWidth));
  }

  function startResize(event: ReactPointerEvent<HTMLDivElement>) {
    dragStart.current = { pointerX: event.clientX, width };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function startMouseResize(event: ReactMouseEvent<HTMLDivElement>) {
    dragStart.current = { pointerX: event.clientX, width };
  }

  return <><button aria-controls="persistent-conversation" aria-expanded={open} aria-label={context.action} className="conversation-launcher" data-surface={context.surface} onClick={(event) => { lastOpener.current = event.currentTarget; setDockOpen(true); }} ref={openButton} type="button"><MessageSquare aria-hidden="true" size={19} /><span><small>{context.label}</small>{context.action}</span><PanelRightOpen aria-hidden="true" size={18} /></button><aside aria-label={context.relationshipId ? 'Professional conversation' : 'WAOOAW Guide'} className="persistent-conversation" data-open={open} id="persistent-conversation" ref={dock} style={{ '--guide-width': `${width}px` } as CSSProperties}><div aria-label="Resize Guide" aria-orientation="vertical" aria-valuemax={560} aria-valuemin={320} aria-valuenow={width} className="conversation-resizer" onKeyDown={(event) => {
    const direction = document.documentElement.dir === 'rtl' ? -1 : 1;
    if (event.key === 'Home') setBoundedWidth(320);
    else if (event.key === 'End') setBoundedWidth(560);
    else if (event.key === 'ArrowLeft') setBoundedWidth(width + 16 * direction);
    else if (event.key === 'ArrowRight') setBoundedWidth(width - 16 * direction);
    else return;
    event.preventDefault();
  }} onMouseDown={startMouseResize} onPointerDown={startResize} role="separator" tabIndex={0} /><button aria-label="Close conversation" className="icon-command conversation-close" onClick={() => setDockOpen(false)} ref={closeButton} type="button"><PanelRightClose aria-hidden="true" size={20} /></button>{context.relationshipId ? <ConversationExperience key={context.relationshipId} relationshipId={context.relationshipId} /> : <PortalGuideExperience currentSurface={context.surface} locale={locale} />}</aside>{open ? <button aria-label="Close conversation overlay" className="conversation-scrim" onClick={() => setDockOpen(false)} type="button" /> : null}</>;
}

export function ConversationContextAction() {
  const context = routeContext(usePathname());
  return <button className="context-conversation-action" onClick={(event) => window.dispatchEvent(new CustomEvent('waooaw:open-conversation', { detail: { opener: event.currentTarget } }))} type="button"><MessageSquare aria-hidden="true" size={17} /><span>{context.action}</span></button>;
}