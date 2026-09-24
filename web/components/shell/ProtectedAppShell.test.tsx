import { fireEvent, render, screen } from '@testing-library/react';
import { ProtectedAppShell } from './ProtectedAppShell';
import { getMessages } from '@/lib/i18n';

jest.mock('next/navigation', () => ({ usePathname: () => '/marketplace' }));
jest.mock('@/components/auth/SignOutCommand', () => ({
  AccountSwitchCommand: () => <button type="button">Switch account</button>,
  SignOutCommand: () => <button type="button">Sign out</button>,
}));
jest.mock('@/components/auth/SessionValidityGuard', () => ({ SessionValidityGuard: () => null }));
jest.mock('@/components/conversation/PersistentConversationDock', () => ({ PersistentConversationDock: () => null }));
jest.mock('./ExperienceControls', () => ({ ExperienceControls: () => null }));
jest.mock('./RouteAwareEmergencyStop', () => ({ RouteAwareEmergencyStop: () => null }));
jest.mock('./AppShell', () => ({
  AppShell: ({
    applicationControls,
    children,
  }: { applicationControls: React.ReactNode; children: React.ReactNode }) => (
    <>
      <div>{applicationControls}</div>
      <main>{children}</main>
    </>
  ),
}));

function requiredDetails(control: HTMLElement): HTMLDetailsElement {
  const details = control.closest('details');
  if (!(details instanceof HTMLDetailsElement)) throw new Error('Account control must be inside details');
  return details;
}

describe('ProtectedAppShell account menu', () => {
  it('closes on an outside pointer interaction', () => {
    render(
      <ProtectedAppShell locale="en" messages={getMessages('en')} variant="customer">
        <button type="button">Page action</button>
      </ProtectedAppShell>
    );
    const toggle = screen.getByLabelText('Account');
    const drawer = requiredDetails(toggle);

    fireEvent.click(toggle);
    expect(drawer).toHaveAttribute('open');
    fireEvent.pointerDown(screen.getByRole('button', { name: 'Page action' }));
    expect(drawer).not.toHaveAttribute('open');
  });

  it('closes on Escape and restores focus to the account control', () => {
    render(
      <ProtectedAppShell locale="en" messages={getMessages('en')} variant="customer">
        <span>Content</span>
      </ProtectedAppShell>
    );
    const toggle = screen.getByLabelText('Account');
    const drawer = requiredDetails(toggle);

    fireEvent.click(toggle);
    fireEvent.keyDown(window, { key: 'Escape' });

    expect(drawer).not.toHaveAttribute('open');
    expect(toggle).toHaveFocus();
  });
});
