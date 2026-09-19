// Implements: architecture/reference/ux/hybrid-ui-acceptance-contract.md §F1 Acceptance Matrix
// Constitutional basis: C-001 (Human Override), C-042 (Vocabulary Mandate), C-059 (Implementation Traceability)

import { fireEvent, render, screen } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { usePathname } from 'next/navigation';
import { AppShell } from './AppShell';
import { ExperienceControls } from './ExperienceControls';
import { OfflineNotice } from './OfflineNotice';
import { ProtectedAppShell } from './ProtectedAppShell';
import { SignInCommand } from '@/components/auth/SignInCommand';
import { AppleSignInCommand } from '@/components/auth/AppleSignInCommand';
import { StateView } from '@/components/system/StateView';
import { messages } from '@/lib/i18n';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));
jest.mock('next/navigation', () => ({ usePathname: jest.fn() }));
jest.mock('@/components/conversation/PersistentConversationDock', () => ({ PersistentConversationDock: () => null }));

describe('F1 shell primitives', () => {
  beforeEach(() => {
    jest.mocked(signIn).mockClear();
    jest.mocked(usePathname).mockReturnValue('/home');
    document.documentElement.lang = 'en';
    document.documentElement.dataset.theme = 'system';
    localStorage.clear();
    Object.defineProperty(navigator, 'onLine', { configurable: true, value: true });
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        schemaVersion: '1.0',
        scope: 'PORTAL',
        contextId: 'context-1',
        items: [],
        authoritativeCursor: 'cursor-0',
        hasMore: false,
        serverTime: '2026-08-10T12:00:00Z',
      }),
    } as Response);
  });

  it('composes public navigation without authenticated controls', () => {
    render(
      <AppShell messages={messages.en} variant="public">
        <p>Public content</p>
      </AppShell>
    );
    expect(screen.getByRole('navigation', { name: messages.en.publicNavigation })).toBeVisible();
    expect(screen.getByRole('link', { name: messages.en.register })).toHaveAttribute('href', '/register');
    expect(screen.queryByRole('button', { name: /Emergency Stop/i })).not.toBeInTheDocument();
  });

  it('keeps the full customer portal visible for an authenticated visitor', () => {
    render(
      <ProtectedAppShell messages={messages.en} variant="customer">
        <p>Visitor content</p>
      </ProtectedAppShell>
    );
    expect(screen.getByRole('navigation', { name: messages.en.customerNavigation })).toBeVisible();
    expect(screen.getByRole('navigation', { name: messages.en.customerMobileNavigation })).toBeVisible();
    expect(screen.getAllByRole('link', { name: 'My Agents' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'Marketplace' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'Alerts' })).toHaveLength(2);
    expect(screen.getByRole('link', { name: 'Profile' })).toHaveAttribute('href', '/profile');
    expect(screen.getByRole('link', { name: 'Billing' })).toHaveAttribute('href', '/profile#billing');
    expect(screen.getByRole('button', { name: 'Sign out' })).toHaveTextContent('Sign out');
  });

  it('composes registered customer navigation with persistent Stop', () => {
    const { container } = render(
      <ProtectedAppShell
        identitySession={{ assuranceLevel: 'AAL2_ACCOUNT' } as never}
        messages={messages.en}
        variant="customer"
      >
        <p>Customer content</p>
      </ProtectedAppShell>
    );
    expect(screen.getAllByRole('link', { name: 'My Agents' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'My Agents' })[0]).toHaveAttribute('href', '/professionals/mine');
    expect(screen.getAllByRole('link', { name: 'Marketplace' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'Marketplace' })[0]).toHaveAttribute('href', '/marketplace');
    expect(screen.getAllByRole('link', { name: 'Alerts' })).toHaveLength(2);
    expect(screen.getAllByRole('link', { name: 'Alerts' })[0]).toHaveAttribute('href', '/alerts');
    expect(screen.getByRole('link', { name: 'Profile' })).toHaveAttribute('href', '/profile');
    expect(container.querySelector('.top-bar')).not.toBeInTheDocument();
    expect(screen.getByText('Account security: Verified')).toBeInTheDocument();
    expect(screen.queryByText('AAL2_ACCOUNT')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'No active work to stop' })).toBeDisabled();
  });

  it('uses client navigation with active state and an accessible persisted rail', () => {
    jest.mocked(usePathname).mockReturnValue('/marketplace');
    render(
      <ProtectedAppShell messages={messages.en} variant="customer">
        <p>Marketplace</p>
      </ProtectedAppShell>
    );

    expect(screen.getAllByRole('link', { name: 'Marketplace' })[0]).toHaveAttribute('aria-current', 'page');
    const toggle = screen.getByRole('button', { name: 'Expand navigation' });
    fireEvent.click(toggle);
    expect(screen.getByRole('button', { name: 'Collapse navigation' })).toHaveAttribute('aria-expanded', 'true');
    expect(localStorage.getItem('waooaw:navigation-expanded')).toBe('true');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(screen.getByRole('button', { name: 'Expand navigation' })).toHaveFocus();
  });

  it('passes an approved active Stop context to the constitutional control', () => {
    render(
      <ProtectedAppShell
        messages={messages.en}
        stopContext={{ contractId: 'contract-1', activeSessionIds: ['session-1'] }}
        variant="customer"
      >
        <p>Active work</p>
      </ProtectedAppShell>
    );
    expect(screen.getByRole('button', { name: 'Emergency Stop' })).toBeEnabled();
  });

  it('uses authenticated relationship scope when the runtime owns active session discovery', () => {
    jest.mocked(usePathname).mockReturnValue('/relationships/relationship-1');
    render(
      <ProtectedAppShell messages={messages.en} variant="customer">
        <p>Relationship</p>
      </ProtectedAppShell>
    );
    expect(screen.getByRole('button', { name: 'Emergency Stop' })).toBeEnabled();
  });

  it('changes locale and theme through durable preferences', async () => {
    const reload = jest.fn();
    render(<ExperienceControls messages={messages.en} reload={reload} />);
    fireEvent.change(screen.getByRole('combobox', { name: 'Language' }), { target: { value: 'ur' } });
    expect(document.cookie).toContain('waooaw-locale=ur');
    expect(reload).toHaveBeenCalledTimes(1);

    const useLight = await screen.findByRole('button', { name: 'Use light theme' });
    fireEvent.click(useLight);
    expect(document.documentElement.dataset.theme).toBe('light');
    expect(document.cookie).toContain('waooaw-theme=light');

    fireEvent.click(screen.getByRole('button', { name: 'Use dark theme' }));
    expect(document.documentElement.dataset.theme).toBe('dark');
    expect(document.cookie).toContain('waooaw-theme=dark');
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
    rerender(
      <StateView
        actionLabel={messages.en.returnHome}
        kind="forbidden"
        title="Access not permitted"
        description="Not allowed"
      />
    );
    expect(screen.getByRole('link', { name: messages.en.returnHome })).toHaveAttribute('href', '/');
  });

  it('uses only the Keycloak sign-in command', () => {
    render(<SignInCommand label={messages.en.signInSecurely} />);
    fireEvent.click(screen.getByRole('button', { name: messages.en.signInSecurely }));
    expect(signIn).toHaveBeenCalledWith('keycloak', { callbackUrl: '/home' });
  });

  it('keeps unavailable Apple authentication local and recommends active alternatives', () => {
    render(<AppleSignInCommand />);

    fireEvent.click(screen.getByRole('button', { name: 'Continue with Apple' }));

    expect(screen.getByRole('alert')).toHaveTextContent(
      'Apple integration is coming soon. Meanwhile use your Google or Meta account.'
    );
    expect(signIn).not.toHaveBeenCalled();
  });
});
