'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-023, C-059, C-063, ADR-051

import { useCallback, useState } from 'react';
import type { WorkbenchSnapshot } from '@/lib/api/workbench-types';
import { problemText, sendWorkbenchCommand, type WorkbenchResult } from '@/lib/workbench-client';
import type { WorkbenchMessages } from '@/lib/workbench-i18n';

export type WorkbenchPanelProps = {
  relationshipId: string;
  snapshot: WorkbenchSnapshot;
  copy: WorkbenchMessages;
  onChanged: () => Promise<void>;
};

type Message = { kind: 'success' | 'error'; text: string };

export function useWorkbenchCommand(relationshipId: string, copy: WorkbenchMessages, onChanged: () => Promise<void>) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<Message | null>(null);

  const run = useCallback(
    async <T,>(path: string, body: unknown, successText?: string): Promise<WorkbenchResult<T>> => {
      setBusy(true);
      setMessage(null);
      const result = await sendWorkbenchCommand<T>(relationshipId, path, body);
      if (result.ok) {
        setMessage({ kind: 'success', text: successText ?? copy.done });
      } else {
        setMessage({ kind: 'error', text: problemText(copy, result) });
      }
      if (result.ok || result.problem.code === 'WORKBENCH_VERSION_CONFLICT') await onChanged();
      setBusy(false);
      return result;
    },
    [copy, onChanged, relationshipId]
  );

  return { busy, message, run, clear: () => setMessage(null) };
}

export function CommandMessage({ message }: { message: Message | null }) {
  if (message === null) return <p aria-live="polite" className="workbench-message" role="status" />;
  return (
    <p
      aria-live={message.kind === 'error' ? 'assertive' : 'polite'}
      className={`workbench-message workbench-message-${message.kind}`}
      role={message.kind === 'error' ? 'alert' : 'status'}
    >
      {message.text}
    </p>
  );
}
