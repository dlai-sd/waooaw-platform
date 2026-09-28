import type { EmploymentRelationshipSummaryV1 } from '@/lib/api/generated/models/EmploymentRelationshipSummaryV1';
import type { EmploymentRelationship, RelationshipEvaluationProjection } from '@/lib/api/relationships';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { RelationshipPreActivation } from './RelationshipPreActivation';

const relationship: EmploymentRelationship = {
  relationshipId: '77699132-98cf-4cb2-b53d-6a2e1f0c7f92',
  agentInstanceId: '28a4536e-0413-4d64-ae7c-04ac7efd9ff1',
  professionalType: 'DIGITAL_MARKETING_LOCAL_SERVICE',
  professionalVersion: '1.0.0',
  agentInstanceMintedAt: new Date('2026-09-09T10:00:00Z'),
  state: 'CONFIGURING',
  stateVersion: 2,
  createdAt: new Date('2026-09-09T10:00:00Z'),
  updatedAt: new Date('2026-09-09T10:05:00Z'),
};

const evaluation: RelationshipEvaluationProjection = {
  relationshipId: relationship.relationshipId,
  lifecycleState: 'CONFIGURING',
  interviewState: 'COMPLETE',
  context: [],
  goals: [],
  skills: [],
};
const relationshipSummary = {
  relationshipId: relationship.relationshipId,
  professionalDisplayName: 'Digital Marketing Professional',
  lifecycleState: 'CONFIGURING',
} as EmploymentRelationshipSummaryV1;
const originalFetch = global.fetch;

describe('RelationshipPreActivation', () => {
  afterEach(() => {
    jest.restoreAllMocks();
    global.fetch = originalFetch;
  });

  it('collects explicit Hire setup before contract or payment', () => {
    render(
      <RelationshipPreActivation
        relationship={relationship}
        relationships={[relationshipSummary]}
        timeline={[]}
        evaluation={evaluation}
        contractJourney={null}
        availableSkills={[
          { skillId: 'MARKET_RESEARCH', displayName: 'Market Research' },
          { skillId: 'CONTENT_STRATEGY', displayName: 'Content Strategy' },
        ]}
      />
    );

    expect(screen.getByRole('heading', { name: 'Configure the professional' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Digital Marketing Professional/ })).toHaveAttribute(
      'aria-current',
      'page'
    );
    expect(screen.getByRole('checkbox', { name: 'Market Research' })).not.toBeChecked();
    expect(screen.getByRole('checkbox', { name: /I confirm this budget and scope/ })).not.toBeChecked();
    expect(screen.getByRole('button', { name: 'Prepare exact contract' })).toBeEnabled();
  });

  it('submits the complete Hire setup and displays a server rejection', async () => {
    const request = jest
      .fn()
      .mockResolvedValueOnce({
        ok: false,
        json: async () => ({ detail: 'Authority scope could not be verified.' }),
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        json: async () => {
          throw new Error('invalid json');
        },
      } as unknown as Response);
    global.fetch = request;
    render(
      <RelationshipPreActivation
        relationship={relationship}
        relationships={[]}
        timeline={[]}
        evaluation={evaluation}
        contractJourney={null}
        availableSkills={[{ skillId: 'MARKET_RESEARCH', displayName: 'Market Research' }]}
      />
    );

    fireEvent.change(screen.getByLabelText('Business name'), { target: { value: 'Acme Dental' } });
    fireEvent.change(screen.getByLabelText('Service location'), { target: { value: 'Pune' } });
    fireEvent.change(screen.getByLabelText('What your business provides'), { target: { value: 'Dental care' } });
    fireEvent.change(screen.getByLabelText('Primary goal'), { target: { value: 'Increase appointments' } });
    fireEvent.change(screen.getByLabelText('How success will be measured'), { target: { value: 'Ten leads' } });
    fireEvent.change(screen.getByLabelText('Monthly authority ceiling (INR)'), { target: { value: '1200' } });
    fireEvent.click(screen.getByRole('checkbox', { name: 'Market Research' }));
    fireEvent.click(screen.getByRole('checkbox', { name: /I confirm this budget and scope/ }));
    fireEvent.click(screen.getByRole('button', { name: 'Prepare exact contract' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Authority scope could not be verified.');
    await waitFor(() => expect(screen.getByRole('button', { name: 'Prepare exact contract' })).toBeEnabled());
    expect(JSON.parse(String(request.mock.calls[0][1]?.body))).toEqual(
      expect.objectContaining({
        budgetCeilingInrPaise: 120000,
        selectedSkillIds: ['MARKET_RESEARCH'],
        authorityScopeConfirmation: 'CONFIRM_AUTHORITY_SCOPE',
      })
    );
    expect(request.mock.calls[0][1]?.headers).toEqual(
      expect.objectContaining({ 'Idempotency-Key': expect.any(String) })
    );

    fireEvent.click(screen.getByRole('button', { name: 'Prepare exact contract' }));
    expect(await screen.findByText('Hire setup could not be completed. No contract was accepted.')).toBeVisible();
  });
});
