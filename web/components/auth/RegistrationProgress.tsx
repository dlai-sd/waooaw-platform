// Implements: work-contracts/WC-083-route-backed-auth-dialog.md §Milestone 2
// Constitutional basis: C-049 (Honest Limitation), C-071 (Accessible status)

import type { IdentityNextAction } from '@/lib/api/generated/models/IdentityNextAction';

const letters = [
  { id: 'waooaw-1', label: 'W' },
  { id: 'waooaw-2', label: 'A' },
  { id: 'waooaw-3', label: 'O' },
  { id: 'waooaw-4', label: 'O' },
  { id: 'waooaw-5', label: 'A' },
  { id: 'waooaw-6', label: 'W' },
] as const;

const progressState: Record<IdentityNextAction, { active: number; label: string }> = {
  COMPLETE_PROFILE: { active: 1, label: 'Profile details' },
  VERIFY_EMAIL: { active: 2, label: 'Email verification' },
  VERIFY_MOBILE: { active: 3, label: 'Optional mobile verification' },
  COMPLETE_REGISTRATION: { active: 4, label: 'Registration review' },
  RESOLVE_DUPLICATE: { active: 4, label: 'Identity confirmation' },
  CONTINUE_TO_DEFAULT_TARGET: { active: 6, label: 'Registration complete' },
  NONE: { active: 6, label: 'Registration complete' },
};

export function RegistrationProgress({ action, pending }: { action: IdentityNextAction; pending: boolean }) {
  const progress = progressState[action];
  return (
    <output
      aria-label={`Registration progress: ${progress.label}`}
      className="registration-progress"
      data-pending={pending || undefined}
    >
      <ol aria-hidden="true">
        {letters.map(({ id, label }, index) => {
          const state =
            progress.active === 6 || index < progress.active
              ? 'complete'
              : index === progress.active
                ? 'active'
                : 'upcoming';
          return (
            <li data-state={state} key={id}>
              {label}
            </li>
          );
        })}
      </ol>
      <span>{progress.label}</span>
    </output>
  );
}
