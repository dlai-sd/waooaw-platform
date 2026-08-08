'use client';

import { CircleStop } from 'lucide-react';
import { useState } from 'react';

interface EmergencyStopProps {
  contractId: string | null;
  activeSessionIds: string[];
}

export function EmergencyStop({ contractId, activeSessionIds }: EmergencyStopProps) {
  const [status, setStatus] = useState<'idle' | 'stopping' | 'confirmed' | 'failed'>('idle');
  const ready = Boolean(contractId && activeSessionIds.length > 0);

  async function stop() {
    if (!ready || !contractId) return;
    setStatus('stopping');
    try {
      const response = await fetch('/api/emergency-stop', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contractId, activeSessionIds }),
      });
      setStatus(response.ok ? 'confirmed' : 'failed');
    } catch {
      setStatus('failed');
    }
  }

  const message = !ready
    ? 'No active work to stop'
    : status === 'stopping'
      ? 'Stopping active work…'
      : status === 'confirmed'
        ? 'Emergency Stop confirmed'
        : status === 'failed'
          ? 'Stop not confirmed. Try again.'
          : 'Emergency Stop';

  return (
    <div className="stop-control" aria-live="polite">
      <button type="button" onClick={stop} disabled={!ready || status === 'stopping' || status === 'confirmed'}>
        <CircleStop aria-hidden="true" size={22} />
        {message}
      </button>
    </div>
  );
}