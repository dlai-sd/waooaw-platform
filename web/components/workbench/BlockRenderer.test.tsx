// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import { render, screen } from '@testing-library/react';
import type { WorkbenchBlock } from '@/lib/api/workbench-types';
import { workbenchMessages } from '@/lib/workbench-i18n';
import { BlockRenderer, destinationHref } from './BlockRenderer';

const copy = workbenchMessages('en');

function block(overrides: Partial<WorkbenchBlock>): WorkbenchBlock {
  return {
    id: 'block-1',
    type: 'TEXT',
    version: 1,
    sensitivity: 'CUSTOMER',
    data: { text: 'Hello there' },
    fallback: [],
    ...overrides,
  } as WorkbenchBlock;
}

describe('BlockRenderer', () => {
  it('renders every kernel block type from its declared data', () => {
    const blocks: WorkbenchBlock[] = [
      block({ id: 'a', type: 'TEXT', data: { text: 'Plain text' } }),
      block({ id: 'b', type: 'CHOICES', data: { choices: [{ choiceId: 'c1', label: 'First choice' }] } }),
      block({
        id: 'c',
        type: 'LIST',
        data: { rows: [{ rowId: 'r1', title: 'Row title', description: 'Row detail' }] },
      }),
      block({
        id: 'd',
        type: 'STATUS',
        data: { itemRef: 'x', state: 'IN_PROGRESS', owner: 'agent', freshness: 'CURRENT' },
      }),
      block({
        id: 'e',
        type: 'METRIC',
        label: 'Reach',
        data: { measureId: 'reach', value: '12', unit: 'people', target: '20', trend: 'UP', freshness: 'CURRENT' },
      }),
      block({
        id: 'f',
        type: 'PLAN',
        data: {
          planVersion: 'p1',
          milestones: [{ milestoneId: 'm1', title: 'Launch', dueMeaning: 'End of month' }],
          calendar: [{ date: '2026-06-03', title: 'Review call' }],
        },
      }),
      block({
        id: 'g',
        type: 'DECISION',
        data: {
          decisionId: 'd1',
          effect: 'Publish post',
          authority: 'You',
          cost: 'One credit',
          confirmLabel: 'Yes',
          cancelLabel: 'No',
        },
      }),
      block({ id: 'h', type: 'FORM', data: { formId: 'goal:x', fields: [{ fieldId: 'a', label: 'Audience' }] } }),
      block({
        id: 'i',
        type: 'EVIDENCE',
        data: { evidenceRef: 'e1', summary: 'Proof of work', producedAt: '2026-06-01T10:00:00Z' },
      }),
    ];
    render(
      <div>
        {blocks.map((item) => (
          <BlockRenderer block={item} copy={copy} key={item.id} />
        ))}
      </div>
    );
    for (const expected of [
      'Plain text',
      'First choice',
      'Row title',
      'In progress',
      'Launch',
      'Review call',
      'Publish post',
      'Audience',
      'Proof of work',
    ]) {
      expect(screen.getAllByText(new RegExp(expected)).length).toBeGreaterThan(0);
    }
    expect(screen.getByRole('img', { name: /Trend/ })).toBeInTheDocument();
  });

  it('shows the declared fallback for an unknown type or a higher version, never raw data', () => {
    render(
      <div>
        <BlockRenderer
          block={block({
            id: 'u',
            type: 'DOMAIN' as WorkbenchBlock['type'],
            data: { secret: 'RAW-DOMAIN-DATA' },
            fallback: [{ type: 'TEXT', data: { text: 'Fallback words' } }],
          })}
          copy={copy}
        />
        <BlockRenderer
          block={block({
            id: 'v',
            version: 2,
            data: { text: 'FUTURE' },
            fallback: [{ type: 'TEXT', data: { text: 'Older words' } }],
          })}
          copy={copy}
        />
        <BlockRenderer block={block({ id: 'w', type: 'DOMAIN' as WorkbenchBlock['type'], fallback: [] })} copy={copy} />
      </div>
    );
    expect(screen.getByText('Fallback words')).toBeInTheDocument();
    expect(screen.getByText('Older words')).toBeInTheDocument();
    expect(screen.getByText(copy.unsupportedBlock)).toBeInTheDocument();
    expect(screen.queryByText('RAW-DOMAIN-DATA')).not.toBeInTheDocument();
    expect(screen.queryByText('FUTURE')).not.toBeInTheDocument();
  });

  it('resolves only a workbench reference to a route and never renders markup from data', () => {
    const id = '0f5d4d3a-6f0c-4b6e-9f30-2d4f6a0c1b11';
    expect(destinationHref(`workbench:${id}`)).toBe(`/relationships/${id}`);
    expect(destinationHref('https://example.test/phish')).toBeNull();
    expect(destinationHref('javascript:alert(1)')).toBeNull();
    expect(destinationHref(undefined)).toBeNull();

    const { container } = render(
      <div>
        <BlockRenderer
          block={block({ id: 'l1', type: 'LINK', data: { label: 'Open it', destinationRef: `workbench:${id}` } })}
          copy={copy}
        />
        <BlockRenderer
          block={block({
            id: 'l2',
            type: 'LINK',
            data: { label: 'Elsewhere', destinationRef: 'https://example.test' },
          })}
          copy={copy}
        />
        <BlockRenderer block={block({ id: 't', data: { text: '<img src=x onerror=alert(1)>' } })} copy={copy} />
      </div>
    );
    expect(screen.getByRole('link', { name: 'Open it' })).toHaveAttribute('href', `/relationships/${id}`);
    expect(screen.queryByRole('link', { name: 'Elsewhere' })).not.toBeInTheDocument();
    expect(screen.getByText('Elsewhere')).toBeInTheDocument();
    expect(container.querySelector('img')).toBeNull();
  });
});
