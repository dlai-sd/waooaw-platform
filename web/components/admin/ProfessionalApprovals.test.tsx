// Implements: work-contracts/WC-175-demo-registration-trial-hire-and-founder-defects.md WC175-R024
// Constitutional basis: C-023, C-059, C-063

import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import type { ProfessionalApproval } from '@/lib/professional-approvals';
import { savePendingStepUp } from '@/lib/step-up-resume';
import { ProfessionalApprovals } from './ProfessionalApprovals';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

const notApproved: ProfessionalApproval = {
  professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
  professionalVersion: '1.0.0',
  displayName: 'Digital Marketing Professional',
  state: 'NOT_APPROVED',
  definitionChanged: false,
  decidedBy: null,
  decidedAt: null,
  reason: null,
  stateVersion: 0,
  actions: ['approve'],
};
const approved: ProfessionalApproval = {
  ...notApproved,
  state: 'APPROVED',
  decidedBy: 'founder-1',
  decidedAt: '2026-12-01T09:00:00Z',
  stateVersion: 1,
  actions: ['suspend', 'retire'],
};

function reply(status: number, body: unknown) {
  return { ok: status < 300, status, json: async () => body } as unknown as Response;
}

function install(handler: (path: string, body: unknown) => Response) {
  const calls: { path: string; body: unknown }[] = [];
  global.fetch = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const path = String(input).replace('/api/admin/professionals/', '');
    const body = init?.body ? JSON.parse(String(init.body)) : null;
    calls.push({ path, body });
    return handler(path, body);
  }) as jest.Mock;
  return calls;
}

describe('ProfessionalApprovals', () => {
  beforeEach(() => {
    window.sessionStorage.clear();
    jest.clearAllMocks();
  });

  it('shows plainly what customers can and cannot do for each state, with only the decisions that apply', () => {
    render(<ProfessionalApprovals initial={[notApproved]} />);

    expect(screen.getByText('Not approved yet')).toBeTruthy();
    expect(screen.getByText(/cannot start a Trial or Hire/)).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Approve for customers' })).toBeTruthy();
    expect(screen.queryByRole('button', { name: 'Suspend' })).toBeNull();
  });

  it('approves in one step and then offers suspend and retire', async () => {
    const calls = install(() => reply(200, approved));
    render(<ProfessionalApprovals initial={[notApproved]} />);

    fireEvent.click(screen.getByRole('button', { name: 'Approve for customers' }));

    await waitFor(() => expect(screen.getByText('Approved for customers')).toBeTruthy());
    expect(calls[0]).toEqual({
      path: 'DIGITAL_MARKETING_LOCAL_SERVICE/versions/1.0.0/approve',
      body: { reason: null },
    });
    expect(screen.getByRole('button', { name: 'Suspend' })).toBeTruthy();
    expect(screen.getByRole('button', { name: 'Retire' })).toBeTruthy();
  });

  it('asks for a reason before suspending and sends it', async () => {
    const calls = install(() =>
      reply(200, { ...approved, state: 'SUSPENDED', reason: 'Paused for a review', actions: ['approve', 'retire'] })
    );
    render(<ProfessionalApprovals initial={[approved]} />);

    fireEvent.click(screen.getByRole('button', { name: 'Suspend' }));
    fireEvent.change(screen.getByLabelText(/Reason for suspending/), { target: { value: 'Paused for a review' } });
    fireEvent.click(screen.getByRole('button', { name: 'Confirm suspend' }));

    await waitFor(() => expect(screen.getByText('Suspended')).toBeTruthy());
    expect(calls[0].body).toEqual({ reason: 'Paused for a review' });
  });

  it('asks for a fresh strong sign-in when the decision is refused for step-up, and continues it after', async () => {
    install(() => reply(403, { code: 'PROFESSIONAL_APPROVAL_STEP_UP_REQUIRED' }));
    render(<ProfessionalApprovals initial={[notApproved]} />);

    fireEvent.click(screen.getByRole('button', { name: 'Approve for customers' }));
    const confirm = await screen.findByRole('button', { name: 'Confirm with multi-factor sign-in' });
    fireEvent.click(confirm);

    expect(signIn).toHaveBeenCalled();
    const calls = install(() => reply(200, approved));
    savePendingStepUp('professionals.decision', {
      professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
      professionalVersion: '1.0.0',
      action: 'approve',
      reason: '',
    });
    render(<ProfessionalApprovals initial={[notApproved]} />);
    await waitFor(() => expect(calls.length).toBe(1));
    expect(calls[0].path).toBe('DIGITAL_MARKETING_LOCAL_SERVICE/versions/1.0.0/approve');
  });

  it('warns that customers are stopped when the shipped definition changed since the approval', () => {
    render(
      <ProfessionalApprovals
        initial={[{ ...approved, definitionChanged: true, actions: ['approve', 'suspend', 'retire'] }]}
      />
    );

    expect(screen.getByRole('alert').textContent).toMatch(/definition changed/);
    expect(screen.getByRole('button', { name: 'Approve for customers' })).toBeTruthy();
  });

  it('says in plain words when a decision is refused or the service cannot be reached', async () => {
    install(() => reply(409, { code: 'PROFESSIONAL_APPROVAL_CONFLICT' }));
    render(<ProfessionalApprovals initial={[notApproved]} />);
    fireEvent.click(screen.getByRole('button', { name: 'Approve for customers' }));
    await waitFor(() => expect(screen.getByText(/Another decision was saved first/)).toBeTruthy());

    global.fetch = jest.fn(async () => {
      throw new Error('offline');
    }) as jest.Mock;
    fireEvent.click(screen.getByRole('button', { name: 'Approve for customers' }));
    await waitFor(() => expect(screen.getByText(/Nothing was changed/)).toBeTruthy());
  });
});
