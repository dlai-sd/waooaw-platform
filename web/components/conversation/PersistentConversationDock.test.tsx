import { fireEvent, render, screen } from '@testing-library/react';
import { ConversationContextAction, PersistentConversationDock, routeContext } from './PersistentConversationDock';

const mockUsePathname = jest.fn();
jest.mock('next/navigation', () => ({ usePathname: () => mockUsePathname() }));
jest.mock('./ConversationExperience', () => ({ ConversationExperience: ({ relationshipId }: { relationshipId: string }) => <div>Professional {relationshipId}</div> }));
jest.mock('./PortalGuideExperience', () => ({ PortalGuideExperience: ({ currentSurface }: { currentSurface: string }) => <div>Guide {currentSurface}</div> }));

describe('PersistentConversationDock', () => {
  beforeEach(() => {
    localStorage.clear();
    mockUsePathname.mockReturnValue('/marketplace');
    Object.defineProperty(window, 'PointerEvent', { configurable: true, value: MouseEvent });
    window.matchMedia = jest.fn().mockReturnValue({ matches: false });
  });

  it('opens the persistent Guide scope for portal routes and restores focus on Escape', () => {
    render(<PersistentConversationDock />);

    const launcher = screen.getByRole('button', { name: /Ask about professionals/ });
    expect(screen.getByText('Guide MARKETPLACE')).toBeInTheDocument();
    fireEvent.click(launcher);
    expect(launcher).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByRole('complementary', { name: 'WAOOAW Guide' })).toHaveAttribute('data-open', 'true');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(launcher).toHaveFocus();
    expect(localStorage.getItem('waooaw:conversation-open')).toBe('false');
  });

  it('uses only the route-selected relationship conversation', () => {
    mockUsePathname.mockReturnValue('/relationships/relationship-one');
    render(<PersistentConversationDock />);

    expect(screen.getByText('Professional relationship-one')).toBeInTheDocument();
    expect(screen.queryByText(/Guide /)).not.toBeInTheDocument();
    expect(screen.getByRole('complementary', { name: 'Professional conversation' })).toBeInTheDocument();
  });

  it('opens from the contextual top-bar command', () => {
    render(<><ConversationContextAction /><PersistentConversationDock /></>);

    const contextualAction = screen.getAllByRole('button', { name: /Ask about professionals/ })[0];
    fireEvent.click(contextualAction);
    expect(screen.getByRole('complementary', { name: 'WAOOAW Guide' })).toHaveAttribute('data-open', 'true');
    fireEvent.keyDown(window, { key: 'Escape' });
    expect(contextualAction).toHaveFocus();
  });

  it('resizes the desktop Guide with bounded keyboard controls', () => {
    render(<PersistentConversationDock />);
    fireEvent.click(screen.getByRole('button', { name: /Ask about professionals/ }));
    const separator = screen.getByRole('separator', { name: 'Resize Guide' });

    expect(separator).toHaveAttribute('aria-valuenow', '400');
    fireEvent.keyDown(separator, { key: 'End' });
    expect(separator).toHaveAttribute('aria-valuenow', '560');
    fireEvent.keyDown(separator, { key: 'ArrowLeft' });
    expect(separator).toHaveAttribute('aria-valuenow', '560');
    fireEvent.keyDown(separator, { key: 'Home' });
    expect(separator).toHaveAttribute('aria-valuenow', '320');
    expect(localStorage.getItem('waooaw:conversation-width')).toBe('320');
  });

  it('resizes the desktop Guide by pointer movement', () => {
    render(<PersistentConversationDock />);
    fireEvent.click(screen.getByRole('button', { name: /Ask about professionals/ }));
    const separator = screen.getByRole('separator', { name: 'Resize Guide' });
    Object.assign(separator, { setPointerCapture: jest.fn(), hasPointerCapture: () => true });

    fireEvent.pointerDown(separator, { clientX: 700, pointerId: 1 });
    fireEvent.pointerMove(separator, { clientX: 620, pointerId: 1 });

    expect(separator).toHaveAttribute('aria-valuenow', '480');
    expect(localStorage.getItem('waooaw:conversation-width')).toBe('480');
  });

  it('covers portal route labels and mouse resizing in both directions', () => {
    expect(routeContext('/alerts')).toMatchObject({ surface: 'ALERTS', action: 'Review alerts' });
    expect(routeContext('/settings')).toMatchObject({ surface: 'SETTINGS', action: 'Ask about settings' });
    expect(routeContext('/profile')).toMatchObject({ surface: 'PROFILE', action: 'Ask about my account' });
    expect(routeContext('/profile/billing')).toMatchObject({ surface: 'BILLING', action: 'Ask about my account' });
    expect(routeContext('/unknown')).toMatchObject({ surface: 'MY_AGENTS', action: 'Ask WAOOAW Guide' });

    document.documentElement.dir = 'rtl';
    render(<PersistentConversationDock />);
    fireEvent.click(screen.getByRole('button', { name: /Ask about professionals/ }));
    const separator = screen.getByRole('separator', { name: 'Resize Guide' });

    fireEvent.mouseDown(separator, { clientX: 700 });
    fireEvent.mouseMove(window, { clientX: 620 });
    expect(separator).toHaveAttribute('aria-valuenow', '320');
    fireEvent.mouseUp(window);
    fireEvent.mouseMove(window, { clientX: 500 });
    expect(separator).toHaveAttribute('aria-valuenow', '320');

    fireEvent.keyDown(separator, { key: 'ArrowRight' });
    expect(separator).toHaveAttribute('aria-valuenow', '336');
    fireEvent.keyDown(separator, { key: 'PageDown' });
    expect(separator).toHaveAttribute('aria-valuenow', '336');
    document.documentElement.dir = '';
  });

  it('contains focus in the compact Guide sheet', () => {
    window.matchMedia = jest.fn().mockReturnValue({ matches: true });
    render(<PersistentConversationDock />);
    fireEvent.click(screen.getByRole('button', { name: /Ask about professionals/ }));
    const close = screen.getByRole('button', { name: 'Close conversation' });
    const separator = screen.getByRole('separator', { name: 'Resize Guide' });
    separator.style.display = 'none';

    close.focus();
    fireEvent.keyDown(window, { key: 'Tab', shiftKey: true });
    expect(close).toHaveFocus();
    fireEvent.keyDown(window, { key: 'Tab' });
    expect(close).toHaveFocus();
  });
});