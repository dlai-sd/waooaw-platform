import { render, screen } from '@testing-library/react';
import { RegistrationProgress } from './RegistrationProgress';

describe('RegistrationProgress', () => {
  it('announces workflow state without inventing percentage progress', () => {
    const { container, rerender } = render(<RegistrationProgress action="VERIFY_EMAIL" pending />);

    expect(screen.getByRole('status')).toHaveAccessibleName('Registration progress: Email verification');
    expect(container.querySelectorAll('[data-state="complete"]')).toHaveLength(2);
    expect(container.querySelectorAll('[data-state="active"]')).toHaveLength(1);
    expect(screen.getByRole('status')).not.toHaveAttribute('aria-valuenow');

    rerender(<RegistrationProgress action="CONTINUE_TO_DEFAULT_TARGET" pending={false} />);
    expect(screen.getByRole('status')).toHaveAccessibleName('Registration progress: Registration complete');
    expect(container.querySelectorAll('[data-state="complete"]')).toHaveLength(6);
  });
});