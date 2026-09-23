import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { PortalGuideExperience } from './PortalGuideExperience';

describe('PortalGuideExperience', () => {
  beforeEach(() => {
    localStorage.clear();
    global.fetch = jest.fn().mockResolvedValueOnce({
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

  afterEach(() => jest.restoreAllMocks());

  it('identifies bounded Guide scope and renders a durable navigation response', async () => {
    jest.mocked(global.fetch).mockResolvedValueOnce({
      ok: true,
      json: async () => ({
        schemaVersion: '1.0',
        scope: 'PORTAL',
        outcome: 'ACCEPTED',
        authoritativeCursor: 'cursor-2',
        replayed: false,
        customerMessage: {
          schemaVersion: '1.0',
          messageId: 'message-1',
          sequence: 1,
          actor: 'CUSTOMER',
          content: [{ schemaVersion: '1.0', blockType: 'TEXT', text: 'Show billing' }],
          capabilities: [],
          currentSurface: 'MY_AGENTS',
          clientMessageId: 'client-1',
          acceptedAt: '2026-08-10T12:01:00Z',
        },
        guideMessage: {
          schemaVersion: '1.0',
          messageId: 'message-2',
          sequence: 2,
          actor: 'GUIDE',
          content: [{ schemaVersion: '1.0', blockType: 'TEXT', text: 'I can take you to billing details.' }],
          capabilities: [{ capabilityType: 'NAVIGATE', label: 'Review billing', destination: '/profile#billing' }],
          currentSurface: 'MY_AGENTS',
          acceptedAt: '2026-08-10T12:01:01Z',
        },
      }),
    } as Response);
    render(<PortalGuideExperience currentSurface="MY_AGENTS" />);

    expect(screen.getByText(/cannot act as an employed professional/)).toBeVisible();
    await screen.findByText(/Ask where to find agents/);
    const guide = screen.getByRole('region', { name: 'WAOOAW Guide' });
    const timeline = guide.querySelector('.portal-guide-timeline');
    const composer = screen.getByLabelText('Ask the Guide').closest('form');
    expect(timeline).toBeTruthy();
    expect(composer?.parentElement).toBe(guide);
    expect(timeline?.contains(composer)).toBe(false);
    const sendButton = screen.getByRole('button', { name: 'Send' });
    expect(sendButton.closest('.portal-guide-composer')).toBeTruthy();
    expect(sendButton).toHaveTextContent('');
    expect(screen.queryByRole('button', { name: /microphone/i })).not.toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('Ask the Guide'), { target: { value: 'Show billing' } });
    fireEvent.click(sendButton);

    expect(await screen.findByText('I can take you to billing details.')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Review billing' })).toHaveAttribute('href', '/profile#billing');
    await waitFor(() => expect(localStorage.getItem('waooaw:conversation:portal:draft')).toBeNull());
    const request = jest.mocked(global.fetch).mock.calls[1];
    expect(request[0]).toBe('/api/interactions/portal');
    expect(JSON.parse(String((request[1] as RequestInit).body))).toMatchObject({
      currentSurface: 'MY_AGENTS',
      expectedCursor: 'cursor-0',
    });
  });

  it('retains the typed problem code and correlation ID for Guide diagnostics', async () => {
    jest
      .mocked(global.fetch)
      .mockReset()
      .mockResolvedValueOnce({
        ok: false,
        status: 503,
        json: async () => ({
          code: 'IDENTITY_DEPENDENCY_UNAVAILABLE',
          correlationId: 'd8f914cf-f258-46f3-a41a-e345d489862a',
          detail: 'Sensitive downstream detail must not be displayed.',
        }),
      } as Response);

    render(<PortalGuideExperience currentSurface="MARKETPLACE" />);

    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent('IDENTITY_DEPENDENCY_UNAVAILABLE');
    expect(alert).toHaveTextContent('d8f914cf-f258-46f3-a41a-e345d489862a');
    expect(alert).not.toHaveTextContent('Sensitive downstream detail');
  });
});
