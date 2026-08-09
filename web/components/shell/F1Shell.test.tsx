// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §F1 Acceptance Matrix
// Constitutional basis: C-001 (Human Override), C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { usePathname } from 'next/navigation';
import { AppShell } from './AppShell';
import { ExperienceControls } from './ExperienceControls';
import { OfflineNotice } from './OfflineNotice';
import { ProtectedAppShell } from './ProtectedAppShell';
import { SignInCommand } from '@/components/auth/SignInCommand';
import { StateView } from '@/components/system/StateView';
import { messages } from '@/lib/i18n';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));
jest.mock('next/navigation', () => ({ usePathname: jest.fn() }));

describe('F1 shell primitives', () => {
  beforeEach(() => {
    jest.mocked(signIn).mockClear();
    jest.mocked(usePathname).mockReturnValue('/home');
    document.documentElement.lang = 'en';
    document.documentElement.dataset.theme = 'system';
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true });
  });

  it('composes public navigation without authenticated controls', () => {
    render(<AppShell messages={messages.en} variant="public"><p>Public content</p></AppShell>);
    expect(screen.getByRole('navigation', { name: messages.en.publicNavigation })).toBeVisible();
    expect(screen.getByRole('link', { name: messages.en.register })).toHaveAttribute('href', '/register');
    expect(screen.queryByRole('button', { name: /Emergency Stop/i })).not.toBeInTheDocument();
  });

  it('composes role-aware customer navigation with persistent Stop', () => {
    render(<ProtectedAppShell messages={messages.en} variant="customer"><p>Customer content</p></ProtectedAppShell>);
    expect(screen.getByRole('navigation', { name: messages.en.customerNavigation })).toBeVisible();
    expect(screen.getByRole('navigation', { name: messages.en.customerMobileNavigation })).toBeVisible();
    expect(screen.getByRole('button', { name: 'No active work to stop' })).toBeDisabled();
  });

  it('passes an approved active Stop context to the constitutional control', () => {
    render(<ProtectedAppShell messages={messages.en} stopContext={{ contractId: 'contract-1', activeSessionIds: ['session-1'] }} variant="customer"><p>Active work</p></ProtectedAppShell>);
    expect(screen.getByRole('button', { name: 'Emergency Stop' })).toBeEnabled();
  });

  it('uses authenticated relationship scope when the runtime owns active session discovery', () => {
    jest.mocked(usePathname).mockReturnValue('/relationships/relationship-1');
    render(<ProtectedAppShell messages={messages.en} variant="customer"><p>Relationship</p></ProtectedAppShell>);
    expect(screen.getByRole('button', { name: 'Emergency Stop' })).toBeEnabled();
  });

  it('changes locale and theme through durable preferences', async () => {
    const reload = jest.fn();
    render(<ExperienceControls messages={messages.en} reload={reload} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Language' }), { target: { value: 'ur' } });
    expect(document.cookie).toContain('waooaw-locale=ur');
    expect(reload).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: 'Use dark theme' }));
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(document.cookie).toContain('waooaw-theme=dark');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Use light theme' })).toBeVisible());
  });

  it('announces offline state without claiming a sent outcome', async () => {
    const { rerender } = render(<OfflineNotice />);
    expect(screen.queryByRole('status')).not.toBeInTheDocument();
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: false });
    fireEvent(window, new Event('offline'));
    rerender(<OfflineNotice />);
    expect(await screen.findByRole('status')).toHaveTextContent('No changes will be sent');
  });

  it('renders stable loading and forbidden states', () => {
    const { rerender } = render(<StateView kind="loading" title="Loading" description="Preparing" />);
    expect(screen.getByRole('heading', { name: 'Loading' })).toBeVisible();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    rerender(<StateView actionLabel={messages.en.returnHome} kind="forbidden" title="Access not permitted" description="Not allowed" />);
    expect(screen.getByRole('link', { name: messages.en.returnHome })).toHaveAttribute('href', '/');
  });

  it('uses only the Keycloak sign-in command', () => {
    render(<SignInCommand label={messages.en.signInSecurely} />);
    fireEvent.click(screen.getByRole('button', { name: messages.en.signInSecurely }));
    expect(signIn).toHaveBeenCalledWith('keycloak', { callbackUrl: '/home' });
  });
});