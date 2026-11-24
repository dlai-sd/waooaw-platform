// Implements: work-contracts/WC-169-paid-hire-and-connected-accounts.md WC169-R018
// Constitutional basis: C-023, C-049, C-059, C-063

import { simulationFixture } from '@/lib/pricing-admin-test-data';
import type { BuildUp } from '@/lib/pricing-admin-types';
import { fireEvent, render, screen } from '@testing-library/react';
import { PackageBuildUp } from './PackageBuildUp';

const complete: BuildUp = {
  costLines: [
    {
      componentId: 'CONTENT_DRAFT',
      threadId: 'llm_pro',
      quantity: 4,
      unitsPerUnit: 3,
      unitCostPaise: 400,
      lineCostPaise: 4800,
      authorized: true,
    },
  ],
  infrastructureSharePaise: 5000,
  costFloorPaise: 9800,
  unauthorizedThreadIds: [],
  uncostedComponentIds: [],
  targetMarginPercent: 40,
  suggestedPriceInclGstPaise: 19300,
  suggestionStatus: 'COMPLETE',
};

const withBuildUp = (buildUp: BuildUp) => ({ ...simulationFixture, buildUp });

test('before a simulation it explains how to get the build-up and shows no suggestion', () => {
  render(<PackageBuildUp onUseSuggestedPrice={jest.fn()} simulation={null} typedPriceInclGstPaise={null} />);
  expect(screen.getByText(/Save the draft, then press Simulate/)).toBeInTheDocument();
  expect(screen.queryByRole('button')).toBeNull();
});

test('a complete build-up shows cost lines, the floor, the margin and offers the suggested price', () => {
  const onUse = jest.fn();
  render(
    <PackageBuildUp onUseSuggestedPrice={onUse} simulation={withBuildUp(complete)} typedPriceInclGstPaise={200000} />
  );
  expect(screen.getByRole('table', { name: 'Cost lines' })).toBeInTheDocument();
  expect(screen.getByText('Cost floor (total cost)')).toBeInTheDocument();
  expect(screen.getByText(/Target margin: 40%/)).toBeInTheDocument();
  expect(screen.getByText(/Suggested price including GST: INR 193.00/)).toBeInTheDocument();
  expect(screen.getByText(/Your price: INR 2,000.00/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: /Put the suggested price in the price box/ }));
  expect(onUse).toHaveBeenCalledWith(19300);
});

test('an unknown or unauthorized cost is shown as unknown and the suggestion is not offered as final', () => {
  const incomplete: BuildUp = {
    ...complete,
    costLines: [
      {
        componentId: 'PROACTIVE_MESSAGE',
        threadId: 'whatsapp_template_utility',
        quantity: 30,
        unitsPerUnit: 1,
        authorized: false,
      },
    ],
    unauthorizedThreadIds: ['whatsapp_template_utility'],
    suggestionStatus: 'INCOMPLETE',
  };
  render(
    <PackageBuildUp
      onUseSuggestedPrice={jest.fn()}
      simulation={withBuildUp(incomplete)}
      typedPriceInclGstPaise={null}
    />
  );
  expect(screen.getAllByText('Unknown')).toHaveLength(2);
  expect(screen.getByText(/rate not authorized/)).toBeInTheDocument();
  expect(screen.getByText(/Do not treat this as a final price/)).toBeInTheDocument();
  expect(screen.queryByRole('button')).toBeNull();
});

test('when there is nothing to suggest it says so', () => {
  const unusable: BuildUp = {
    ...complete,
    suggestedPriceInclGstPaise: undefined,
    targetMarginPercent: undefined,
    suggestionStatus: 'UNUSABLE',
  };
  render(
    <PackageBuildUp onUseSuggestedPrice={jest.fn()} simulation={withBuildUp(unusable)} typedPriceInclGstPaise={null} />
  );
  expect(screen.getByText(/Suggested price including GST: none/)).toBeInTheDocument();
  expect(screen.getByText(/No suggestion/)).toBeInTheDocument();
});
