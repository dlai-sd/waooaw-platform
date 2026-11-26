// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C5-05
// Constitutional basis: C-023, C-059, C-063

import { fireEvent, render, screen } from '@testing-library/react';
import { signIn } from 'next-auth/react';
import { StepUpCommand } from './StepUpCommand';

jest.mock('next-auth/react', () => ({ signIn: jest.fn() }));

beforeEach(() => window.sessionStorage.clear());
afterEach(() => jest.clearAllMocks());

test('remembers the interrupted action before the sign-in leaves the page', () => {
  render(<StepUpCommand payload={{ id: 'a1' }} pendingKey="screen.action" />);

  fireEvent.click(screen.getByRole('button', { name: 'Confirm with multi-factor sign-in' }));

  const remembered = JSON.parse(window.sessionStorage.getItem('waooaw.step-up.screen.action') ?? '{}');
  expect(remembered).toMatchObject({ key: 'screen.action', payload: { id: 'a1' } });
  expect(typeof remembered.savedAt).toBe('number');
  expect(signIn).toHaveBeenCalledWith('keycloak', expect.objectContaining({ waooawIntent: 'LOGIN' }), {
    prompt: 'login',
    max_age: '0',
    acr_values: '2',
  });
});

test('remembers nothing when no key is given', () => {
  render(<StepUpCommand />);

  fireEvent.click(screen.getByRole('button', { name: 'Confirm with multi-factor sign-in' }));

  expect(window.sessionStorage.length).toBe(0);
  expect(signIn).toHaveBeenCalledTimes(1);
});
