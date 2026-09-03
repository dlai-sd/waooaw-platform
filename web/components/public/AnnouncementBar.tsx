'use client';

// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §10.2 (WC-02)
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)

import { X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

const storageKey = 'waooaw-announcement';

export type PublicAnnouncement = Readonly<{ enabled: boolean; message: string; href: string; revision: string }>;

type Dismissal = Readonly<{ campaignRevision: string; dismissed: true }>;

function readDismissal(): Dismissal | null {
  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Dismissal>;
    return parsed.dismissed === true && typeof parsed.campaignRevision === 'string' ? { campaignRevision: parsed.campaignRevision, dismissed: true } : null;
  } catch {
    return null;
  }
}

export function AnnouncementBar({ announcement }: { announcement: PublicAnnouncement }) {
  const active = announcement.enabled && announcement.message.length > 0;
  const [dismissed, setDismissed] = useState(false);
  const barRef = useRef<HTMLDivElement>(null);
  const visible = active && !dismissed;

  // Dismissal is decided after mount only; it reads no identity or consent state, only campaign revision.
  useEffect(() => {
    if (active) setDismissed(readDismissal()?.campaignRevision === announcement.revision);
  }, [active, announcement.revision]);

  useEffect(() => {
    function updateOffset() {
      document.documentElement.style.setProperty('--announcement-offset', visible && barRef.current ? `${barRef.current.getBoundingClientRect().height}px` : '0px');
    }
    updateOffset();
    if (!visible) return undefined;
    window.addEventListener('resize', updateOffset);
    return () => window.removeEventListener('resize', updateOffset);
  }, [visible]);

  if (!visible) return null;

  function dismiss() {
    window.localStorage.setItem(storageKey, JSON.stringify({ campaignRevision: announcement.revision, dismissed: true }));
    setDismissed(true);
  }

  return (
    <div className="announcement-bar" ref={barRef} role="region" aria-label="Announcement">
      <p>{announcement.href ? <a href={announcement.href}>{announcement.message}</a> : announcement.message}</p>
      <button aria-label="Dismiss announcement" className="announcement-dismiss" onClick={dismiss} type="button"><X aria-hidden="true" size={18} /></button>
    </div>
  );
}
