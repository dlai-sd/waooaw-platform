import { render, screen, waitFor } from '@testing-library/react';
import { MyAgentsSelection } from './MyAgentsSelection';

const originalFetch = global.fetch;

describe('MyAgentsSelection', () => {
  afterEach(() => {
    global.fetch = originalFetch;
  });

  it('announces and focuses only the authoritative selected card without reordering', async () => {
    const selectedId = '22222222-2222-4222-8222-222222222222';
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        relationshipId: selectedId,
        confirmation: 'Trial started',
        nextActionLabel: 'Open conversation',
      }),
    });
    document.body.innerHTML = `<ul><li data-relationship-id="11111111-1111-4111-8111-111111111111" tabindex="-1">First</li><li data-relationship-id="${selectedId}" tabindex="-1">Second</li></ul>`;

    render(<MyAgentsSelection />);

    expect(await screen.findByText('Trial started')).toBeVisible();
    const cards = document.querySelectorAll<HTMLElement>('[data-relationship-id]');
    expect(cards[0]).toHaveTextContent('First');
    expect(cards[1]).toHaveTextContent('Second');
    expect(cards[1]).toHaveAttribute('data-selected', 'true');
    await waitFor(() => expect(cards[1]).toHaveFocus());
    expect(global.fetch).toHaveBeenCalledWith('/professionals/mine/selection', {
      method: 'POST',
      cache: 'no-store',
    });
  });

  it('shows no confirmation or selection for an empty consume response', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: true, status: 204 });
    document.body.innerHTML = '<div data-relationship-id="22222222-2222-4222-8222-222222222222" tabindex="-1">Agent</div>';

    render(<MyAgentsSelection />);

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(screen.queryByText(/started|hired/i)).not.toBeInTheDocument();
    expect(document.querySelector('[data-selected="true"]')).toBeNull();
  });

  it('prefers the visible responsive card when the shell has duplicate DOM instances', async () => {
    const selectedId = '22222222-2222-4222-8222-222222222222';
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ relationshipId: selectedId, confirmation: 'Trial started', nextActionLabel: 'Open' }),
    });
    document.body.innerHTML = `<div data-relationship-id="${selectedId}" tabindex="-1">Hidden</div><div data-relationship-id="${selectedId}" tabindex="-1">Visible</div>`;
    const cards = document.querySelectorAll<HTMLElement>('[data-relationship-id]');
    Object.defineProperty(cards[1], 'offsetParent', { configurable: true, value: document.body });

    render(<MyAgentsSelection />);

    await screen.findByText('Trial started');
    expect(cards[0]).not.toHaveAttribute('data-selected');
    expect(cards[1]).toHaveAttribute('data-selected', 'true');
    expect(cards[1]).toHaveFocus();
  });
});