'use client';

// Implements: architecture/reference/components/identity-boundary.md §3 Approved Authentication Paths
// Constitutional basis: C-026 (honest limitation), C-059 (Implementation Traceability)

import { useState } from 'react';

const unavailableMessage = 'Apple integration is coming soon. Meanwhile use your Google or Meta account.';

export function AppleSignInCommand() {
  const [showUnavailable, setShowUnavailable] = useState(false);

  return <div className="apple-sign-in">
    <button
      className="provider-command"
      type="button"
      aria-describedby={showUnavailable ? 'apple-integration-status' : undefined}
      onClick={() => setShowUnavailable(true)}
    >
      Continue with Apple
    </button>
    {showUnavailable ? <p id="apple-integration-status" role="alert">
      <strong>{unavailableMessage}</strong>
    </p> : null}
  </div>;
}