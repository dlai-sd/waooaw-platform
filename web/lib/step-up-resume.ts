'use client';

// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008
// Constitutional basis: C-023, C-059, C-063
// The multi-factor step-up leaves the page and comes back to it. Before leaving, the interrupted action is remembered
// here (ids and choices only, never a secret or a credential value) so the screen can pick it up again once.

import { useEffect, useRef, useState } from 'react';

export const stepUpTtlMs = 10 * 60 * 1000;
export const stepUpResumingText = 'Resuming your action after sign-in…';
export const stepUpSignedInText = (button: string) =>
  `You are signed in with extra security. Press ${button} to continue.`;

const storagePrefix = 'waooaw.step-up.';

export type PendingStepUp<T = unknown> = { key: string; payload: T; savedAt: number };

function store(): Storage | null {
  try {
    return typeof window === 'undefined' ? null : window.sessionStorage;
  } catch {
    return null;
  }
}

function parse<T>(key: string, raw: string | null, now: number): PendingStepUp<T> | null {
  if (raw === null) return null;
  try {
    const value = JSON.parse(raw) as Partial<PendingStepUp<T>> | null;
    if (
      value === null ||
      typeof value !== 'object' ||
      value.key !== key ||
      typeof value.savedAt !== 'number' ||
      now - value.savedAt > stepUpTtlMs ||
      now < value.savedAt
    )
      return null;
    return { key, payload: value.payload as T, savedAt: value.savedAt };
  } catch {
    return null;
  }
}

// Remembers one interrupted action under `key`; a later save under the same key replaces it.
export function savePendingStepUp(key: string, payload: unknown = {}, now: number = Date.now()): void {
  try {
    store()?.setItem(`${storagePrefix}${key}`, JSON.stringify({ key, payload, savedAt: now }));
  } catch {
    return;
  }
}

// Reads the remembered action without using it up; expired or damaged entries are dropped.
export function peekPendingStepUp<T = unknown>(key: string, now: number = Date.now()): PendingStepUp<T> | null {
  const area = store();
  if (!area) return null;
  const pending = parse<T>(key, area.getItem(`${storagePrefix}${key}`), now);
  if (!pending) area.removeItem(`${storagePrefix}${key}`);
  return pending;
}

// Reads the remembered action and forgets it, so it can run only once.
export function consumePendingStepUp<T = unknown>(key: string, now: number = Date.now()): PendingStepUp<T> | null {
  const pending = peekPendingStepUp<T>(key, now);
  if (pending) store()?.removeItem(`${storagePrefix}${key}`);
  return pending;
}

// Finds a remembered action whose key starts with `prefix`, without using it up.
export function findPendingStepUp<T = unknown>(prefix: string, now: number = Date.now()): PendingStepUp<T> | null {
  const area = store();
  if (!area) return null;
  const keys: string[] = [];
  for (let index = 0; index < area.length; index += 1) {
    const name = area.key(index);
    if (name?.startsWith(`${storagePrefix}${prefix}`)) keys.push(name.slice(storagePrefix.length));
  }
  for (const key of keys) {
    const pending = peekPendingStepUp<T>(key, now);
    if (pending) return pending;
  }
  return null;
}

// Runs `resume` once with the action remembered under `key`, when the screen opens after the step-up (and `enabled`).
// Returns true while an asynchronous `resume` is still running, so the screen can say it is resuming.
export function useResumeAfterStepUp<T = unknown>(
  key: string,
  resume: (payload: T) => void | Promise<void>,
  enabled = true
): boolean {
  const [resuming, setResuming] = useState(false);
  const latest = useRef(resume);
  latest.current = resume;
  const started = useRef(false);

  useEffect(() => {
    if (!enabled || started.current) return;
    started.current = true;
    const pending = consumePendingStepUp<T>(key);
    if (!pending) return;
    setResuming(true);
    void (async () => {
      try {
        await latest.current(pending.payload);
      } catch {
        return;
      } finally {
        setResuming(false);
      }
    })();
  }, [key, enabled]);

  return resuming;
}
