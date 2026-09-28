'use client';

// Implements: WC-107 R015-R016 authoritative confirmation and selected relationship focus
// Constitutional basis: C-023, C-049, C-059, C-063

import { CheckCircle2 } from 'lucide-react';
import { useEffect, useState } from 'react';

interface SelectionConfirmation {
  relationshipId: string;
  confirmation: string;
  nextActionLabel: string;
}

export function MyAgentsSelection() {
  const [selection, setSelection] = useState<SelectionConfirmation | null>(null);

  useEffect(() => {
    let active = true;
    void fetch('/professionals/mine/selection', { method: 'POST', cache: 'no-store' })
      .then(async (response) => (response.ok && response.status !== 204 ? response.json() : null))
      .then((result: SelectionConfirmation | null) => {
        if (!active || !result) return;
        const cards = Array.from(
          document.querySelectorAll<HTMLElement>(`[data-relationship-id="${result.relationshipId}"]`)
        );
        const card = cards.find((candidate) => candidate.offsetParent !== null) ?? cards[0];
        if (!card) return;
        card.dataset.selected = 'true';
        card.setAttribute('aria-describedby', 'my-agents-selection-confirmation');
        setSelection(result);
        card.focus();
      })
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, []);

  return (
    <output className="my-agents-confirmation" id="my-agents-selection-confirmation">
      {selection ? (
        <>
          <CheckCircle2 aria-hidden="true" size={20} />
          <span>
            <strong>{selection.confirmation}</strong> {selection.nextActionLabel}
          </span>
        </>
      ) : null}
    </output>
  );
}