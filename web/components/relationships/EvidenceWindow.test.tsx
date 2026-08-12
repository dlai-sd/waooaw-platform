import { fireEvent, render, screen } from '@testing-library/react';
import { EvidenceWindow } from './EvidenceWindow';

const evidence = {
  schemaVersion: '1.0' as const,
  relationshipId: '5f33925b-fb0c-4366-8414-7f85309639b9',
  items: [{ evidenceId: '2af901e4-e0db-49a6-bfcc-bb8e575159f2', subject: 'TRIAL_STARTED', state: 'RECORDED' as const }],
};

describe('EvidenceWindow', () => {
  afterEach(() => jest.restoreAllMocks());

  it('offers the completed canonical export without claiming participant acknowledgement', async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ schemaVersion: '1.0', exportId: 'export-1', status: 'COMPLETED', downloadUrl: 'https://evidence.example/export-1' }),
    } as Response);
    render(<EvidenceWindow relationshipId={evidence.relationshipId} evidence={evidence} />);

    fireEvent.click(screen.getByRole('button', { name: 'Export evidence' }));

    expect(await screen.findByText('Export ready')).toBeVisible();
    expect(screen.getByRole('link', { name: 'Download evidence export' })).toHaveAttribute('href', 'https://evidence.example/export-1');
    expect(screen.getByText('Participant observation unresolved')).toBeVisible();
  });

  it('keeps an unsuccessful export explicitly unresolved', async () => {
    global.fetch = jest.fn().mockResolvedValue({ ok: false } as Response);
    render(<EvidenceWindow relationshipId={evidence.relationshipId} evidence={evidence} />);

    fireEvent.click(screen.getByRole('button', { name: 'Export evidence' }));

    expect(await screen.findByText('Export unresolved')).toBeVisible();
    expect(screen.queryByRole('link', { name: 'Download evidence export' })).not.toBeInTheDocument();
  });
});