// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §F1 Acceptance Matrix
// Constitutional basis: C-001 (Human Override), C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { AppShell } from './AppShell';
import { ExperienceControls } from './ExperienceControls';
import { OfflineNotice } from './OfflineNotice';
import { SignInCommand } from '@/components/auth/SignInCommand';
import { StateView } from '@/components/system/StateView';

const refresh = jest.fn();

jest.mock('next/navigation', () => ({ useRouter: () => ({ refresh }) }));
jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

describe('F1 shell primitives', () => {
  beforeEach(() => {
    refresh.mockClear();
    jest.mocked(signIn).mockClear();
    document.documentElement.lang = 'en';
    document.documentElement.dataset.theme = 'system';
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true });
  });

  it('composes public navigation without authenticated controls', () => {
    render(<AppShell variant="public"><p>Public content</p></AppShell>);
    expect(screen.getByRole('navigation', { name: 'Public navigation' })).toBeVisible();
    expect(screen.getByRole('link', { name: 'Register' })).toHaveAttribute('href', '/register');
    expect(screen.queryByRole('button', { name: /Emergency Stop/i })).not.toBeInTheDocument();
  });

  it('composes role-aware customer navigation with persistent Stop', () => {
    render(<AppShell variant="customer"><p>Customer content</p></AppShell>);
    expect(screen.getByRole('navigation', { name: 'Customer navigation' })).toBeVisible();
    expect(screen.getByRole('navigation', { name: 'Customer mobile navigation' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'No active work to stop' })).toBeDisabled();
  });

  it('changes locale and theme through durable preferences', async () => {
    render(<ExperienceControls />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Language' }), { target: { value: 'ur' } });
    expect(document.cookie).toContain('waooaw-locale=ur');
    expect(refresh).toHaveBeenCalledTimes(1);

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
    rerender(<StateView kind="forbidden" title="Access not permitted" description="Not allowed" />);
    expect(screen.getByRole('link', { name: /Return home/ })).toHaveAttribute('href', '/');
  });

  it('uses only the Keycloak sign-in command', () => {
    render(<SignInCommand />);
    fireEvent.click(screen.getByRole('button', { name: /Sign in securely/ }));
    expect(signIn).toHaveBeenCalledWith('keycloak', { callbackUrl: '/home' });
  });
});