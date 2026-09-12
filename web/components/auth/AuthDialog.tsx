'use client';

// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Constitutional basis: C-059 (Implementation Traceability), C-071 (Accessible interaction)

import { X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import type { MouseEvent, ReactNode } from 'react';
import { useEffect, useRef } from 'react';
import { useAuthJourney } from './AuthJourney';
import { safePublicReturnTarget } from '@/lib/safe-return';

export function AuthDialog({ children, routeReady = true }: { children: ReactNode; routeReady?: boolean }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const router = useRouter();
  const journey = useAuthJourney();
  const originRef = useRef('/');
  const origin = safePublicReturnTarget(journey?.current.origin);
  const trigger = journey?.current.trigger;
  const completeLaunch = journey?.completeLaunch;

  useEffect(() => {
    originRef.current = origin;
    returnFocusRef.current = trigger ?? (document.activeElement instanceof HTMLElement ? document.activeElement : null);
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    if (routeReady) completeLaunch?.();
    return () => {
      if (returnFocusRef.current?.isConnected) {
        returnFocusRef.current.focus();
        return;
      }
      const fallback = document.querySelector<HTMLElement>('main');
      if (fallback) {
        fallback.setAttribute('tabindex', '-1');
        fallback.focus();
      }
    };
  }, [completeLaunch, origin, routeReady, trigger]);

  function dismiss() {
    journey?.cancelLaunch();
    dialogRef.current?.close();
    router.replace(originRef.current, { scroll: false });
  }

  function dismissBackdrop(event: MouseEvent<HTMLDialogElement>) {
    if (event.target === event.currentTarget) dismiss();
  }

  return (
    <dialog
      aria-labelledby="auth-dialog-title"
      className="auth-dialog"
      onCancel={(event) => { event.preventDefault(); dismiss(); }}
      onClick={dismissBackdrop}
      ref={dialogRef}
    >
      <div className="auth-dialog-panel">
        <button aria-label="Close" className="auth-dialog-close" onClick={dismiss} type="button">
          <X aria-hidden="true" size={20} />
        </button>
        {children}
      </div>
    </dialog>
  );
}