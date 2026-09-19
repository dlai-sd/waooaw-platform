'use client';

import { MessageSquare } from 'lucide-react';

export function OpenConversationCommand({ label }: { label: string }) {
  return (
    <button
      className="secondary-link"
      onClick={(event) =>
        window.dispatchEvent(new CustomEvent('waooaw:open-conversation', { detail: { opener: event.currentTarget } }))
      }
      type="button"
    >
      <MessageSquare aria-hidden="true" size={17} />
      {label}
    </button>
  );
}
