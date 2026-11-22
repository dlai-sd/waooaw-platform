'use client';

// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Implements: work-contracts/WC-148-founder-provider-credential-registry-screen.md WC148-R002, WC148-R006
// Constitutional basis: C-023, C-059, C-063

import { signIn } from 'next-auth/react';

// The fresh multi-factor sign-in every Founder write needs; shared by the pricing and provider consoles.
export function StepUpCommand() {
  return (
    <p>
      <button
        className="secondary-link"
        onClick={() =>
          void signIn(
            'keycloak',
            { callbackUrl: window.location.href, waooawIntent: 'LOGIN' },
            { prompt: 'login', max_age: '0', acr_values: '2' }
          )
        }
        type="button"
      >
        Confirm with multi-factor sign-in
      </button>
    </p>
  );
}
