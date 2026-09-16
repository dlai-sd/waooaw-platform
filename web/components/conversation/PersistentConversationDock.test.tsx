import { fireEvent, render, screen } from '@testing-library/react';
import { ConversationContextAction, PersistentConversationDock } from './PersistentConversationDock';

const mockUsePathname = jest.fn();
jest.mock('next/navigation', () => ({ usePathname: () => mockUsePathname() }));
jest.mock('./ConversationExperience', () => ({ ConversationExperience: ({ relationshipId }: { relationshipId: string }) => <div>Professional {relationshipId}</div> }));
jest.mock('./PortalGuideExperience', () => ({ PortalGuideExperience: ({ currentSurface }: { currentSurface: string }) => <div>Guide {currentSurface}</div> }));

describe('PersistentConversationDock', () => {
  beforeEach(() => {
    localStorage.clear();
    mockUsePathname.mockReturnValue('/marketplace');
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
});