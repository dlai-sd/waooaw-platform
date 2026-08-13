import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { OfferabilityWorkbench } from './OfferabilityWorkbench';

const response = (body: object, ok = true) => ({ ok, json: async () => body }) as Response;
type FetchMock = jest.Mock<Promise<Response>, [RequestInfo | URL, RequestInit?]>;

afterEach(() => {
  jest.restoreAllMocks();
  delete (global as { fetch?: typeof fetch }).fetch;
});

test('submits price only and renders the evidence-backed decision', async () => {
  const fetchMock = jest.fn().mockResolvedValue(response({
    schemaVersion: '1.0',
    decisionId: '49ef8e91-b83f-43f8-b829-13b9bbf857ce',
    relationshipId: '3d0deade-9890-46d8-8dd3-530a23b54102',
    disposition: 'ALLOW',
    directContributionPaise: 2000,
    policyVersion: 'FA-047-v1',
    ownerVersions: { WBE: 'validation-7' },
    reasons: [],
    evidenceId: '8a5bc17d-1e71-4fb9-99c6-b88dd07525b3',
    producedAt: '2026-08-13T09:00:00Z',
    expiresAt: '2026-08-14T09:00:00Z',
  })) as FetchMock;
  global.fetch = fetchMock;
  render(<OfferabilityWorkbench />);

  fireEvent.change(screen.getByLabelText('Relationship ID'), { target: { value: '3d0deade-9890-46d8-8dd3-530a23b54102' } });
  fireEvent.change(screen.getByLabelText('Customer price (INR)'), { target: { value: '70.00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Evaluate offer' }));

  await screen.findByText('ALLOW');
  expect(screen.getByText('₹20.00 direct contribution')).toBeInTheDocument();
  expect(screen.getByText('8a5bc17d-1e71-4fb9-99c6-b88dd07525b3')).toBeInTheDocument();
  const submitted = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
  expect(submitted).toMatchObject({ proposedPricePaise: 7000, agentType: 'DMA', bundleTier: 'STARTER' });
  expect(submitted.idempotencyKey).toEqual(expect.any(String));
  expect(submitted).not.toHaveProperty('costFloorPaise');
});

test('shows a fail-closed unavailable state', async () => {
  const fetchMock = jest.fn().mockResolvedValue(response({ code: 'OFFERABILITY_UNAVAILABLE' }, false));
  global.fetch = fetchMock;
  render(<OfferabilityWorkbench />);

  fireEvent.change(screen.getByLabelText('Relationship ID'), { target: { value: '3d0deade-9890-46d8-8dd3-530a23b54102' } });
  fireEvent.change(screen.getByLabelText('Customer price (INR)'), { target: { value: '70.00' } });
  fireEvent.submit(screen.getByRole('button', { name: 'Evaluate offer' }).closest('form')!);

  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Decision unavailable'));
  fireEvent.submit(screen.getByRole('button', { name: 'Evaluate offer' }).closest('form')!);
  await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(2));
  const firstAttempt = JSON.parse(String(fetchMock.mock.calls[0][1]?.body));
  const retry = JSON.parse(String(fetchMock.mock.calls[1][1]?.body));
  expect(retry.idempotencyKey).toBe(firstAttempt.idempotencyKey);
  expect(screen.queryByText('ALLOW')).not.toBeInTheDocument();
});

test('renders a non-allow decision with its reasons', async () => {
  global.fetch = jest.fn().mockResolvedValue(response({
    schemaVersion: '1.0',
    decisionId: '49ef8e91-b83f-43f8-b829-13b9bbf857ce',
    relationshipId: '3d0deade-9890-46d8-8dd3-530a23b54102',
    disposition: 'BLOCK',
    directContributionPaise: -100,
    policyVersion: 'FA-047-v1',
    ownerVersions: { WBE: 'validation-8' },
    reasons: ['COMMERCIAL_FLOOR_FAILED'],
    evidenceId: '8a5bc17d-1e71-4fb9-99c6-b88dd07525b3',
    producedAt: '2026-08-13T09:00:00Z',
    expiresAt: '2026-08-14T09:00:00Z',
  }));
  render(<OfferabilityWorkbench />);

  fireEvent.change(screen.getByLabelText('Relationship ID'), { target: { value: '3d0deade-9890-46d8-8dd3-530a23b54102' } });
  fireEvent.change(screen.getByLabelText('Customer price (INR)'), { target: { value: '49.00' } });
  fireEvent.click(screen.getByRole('button', { name: 'Evaluate offer' }));

  await screen.findByText('BLOCK');
  expect(screen.getByText('COMMERCIAL FLOOR FAILED')).toBeInTheDocument();
  expect(screen.queryByRole('alert')).not.toBeInTheDocument();
});