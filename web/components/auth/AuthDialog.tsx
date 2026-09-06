'use client';

// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 1
// Constitutional basis: C-059 (Implementation Traceability), C-071 (Accessible interaction)

import { X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import type { MouseEvent, ReactNode } from 'react';
import { useEffect, useRef } from 'react';

export function AuthDialog({ children }: { children: ReactNode }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const returnFocusRef = useRef<HTMLElement | null>(null);
  const router = useRouter();

  useEffect(() => {
    returnFocusRef.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    if (dialog && !dialog.open) dialog.showModal();
    return () => returnFocusRef.current?.focus();
  }, []);

  function dismiss() {
    dialogRef.current?.close();
    router.back();
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