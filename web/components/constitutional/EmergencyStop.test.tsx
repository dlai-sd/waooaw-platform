import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { EmergencyStop } from './EmergencyStop';

describe('EmergencyStop', () => {
  it('does not claim stop capability without an active target', () => {
    render(<EmergencyStop contractId={null} activeSessionIds={[]} />);
    expect(screen.getByRole('button', { name: 'No active work to stop' })).toBeDisabled();
  });

  it('waits for confirmation before showing stopped', async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: true });
    const stopped = jest.fn();
    window.addEventListener('waooaw:relationship-stopped', stopped);
    global.fetch = fetchMock;
    render(<EmergencyStop contractId="contract-1" activeSessionIds={['session-1']} />);

    fireEvent.click(screen.getByRole('button', { name: 'Emergency Stop' }));
    expect(screen.getByRole('button', { name: 'Stopping active work…' })).toBeDisabled();
    await waitFor(() => expect(screen.getByRole('button', { name: 'Emergency Stop confirmed' })).toBeDisabled());
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(stopped).toHaveBeenCalledTimes(1);
    expect((stopped.mock.calls[0][0] as CustomEvent).detail).toEqual({ relationshipId: 'contract-1' });
    window.removeEventListener('waooaw:relationship-stopped', stopped);
  });

  it('lets the runtime halt all known sessions when only contract scope is known', async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: true });
    global.fetch = fetchMock;
    render(<EmergencyStop contractId="contract-1" activeSessionIds={[]} />);

    fireEvent.click(screen.getByRole('button', { name: 'Emergency Stop' }));
    await waitFor(() => expect(fetchMock).toHaveBeenCalledWith('/api/emergency-stop', expect.objectContaining({
      body: JSON.stringify({ contractId: 'contract-1' }),
    })));
  });

  it('does not show confirmation when the stop request fails', async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: false });
    global.fetch = fetchMock;
    render(<EmergencyStop contractId="contract-1" activeSessionIds={['session-1']} />);

    fireEvent.click(screen.getByRole('button', { name: 'Emergency Stop' }));
    await waitFor(() => expect(screen.getByRole('button', { name: 'Stop not confirmed. Try again.' })).toBeEnabled());
  });
});