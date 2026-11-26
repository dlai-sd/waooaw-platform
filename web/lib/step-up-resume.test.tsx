// Implements: work-contracts/WC-171-agent-navigation-alerts-and-oversight.md WC171-R008
// Constitutional basis: C-023, C-059, C-063

import { renderHook, waitFor } from '@testing-library/react';
import {
  consumePendingStepUp,
  findPendingStepUp,
  peekPendingStepUp,
  savePendingStepUp,
  stepUpTtlMs,
  useResumeAfterStepUp,
} from './step-up-resume';

beforeEach(() => window.sessionStorage.clear());

describe('pending step-up actions', () => {
  it('remembers an action under its key and uses it up on consume', () => {
    savePendingStepUp('screen.action', { id: 'a1' }, 1_000);

    expect(peekPendingStepUp('screen.action', 2_000)).toEqual({
      key: 'screen.action',
      payload: { id: 'a1' },
      savedAt: 1_000,
    });
    expect(consumePendingStepUp('screen.action', 2_000)?.payload).toEqual({ id: 'a1' });
    expect(consumePendingStepUp('screen.action', 2_000)).toBeNull();
  });

  it('forgets an action after ten minutes', () => {
    savePendingStepUp('screen.action', { id: 'a1' }, 1_000);

    expect(peekPendingStepUp('screen.action', 1_000 + stepUpTtlMs + 1)).toBeNull();
    expect(window.sessionStorage.length).toBe(0);
  });

  it('ignores damaged entries and entries saved under another key', () => {
    window.sessionStorage.setItem('waooaw.step-up.screen.action', '{not json');
    expect(peekPendingStepUp('screen.action')).toBeNull();
    window.sessionStorage.setItem(
      'waooaw.step-up.screen.action',
      JSON.stringify({ key: 'other', payload: {}, savedAt: Date.now() })
    );
    expect(peekPendingStepUp('screen.action')).toBeNull();
  });

  it('finds an action by key prefix without using it up', () => {
    savePendingStepUp('providers.panel.p2', { providerId: 'p2' });
    savePendingStepUp('access.decision', { requestId: 'r1' });

    expect(findPendingStepUp<{ providerId: string }>('providers.panel.')?.payload.providerId).toBe('p2');
    expect(findPendingStepUp('providers.panel.')).not.toBeNull();
    expect(findPendingStepUp('missing.')).toBeNull();
  });
});

describe('useResumeAfterStepUp', () => {
  it('runs the remembered action once with its payload and reports that it is resuming', async () => {
    savePendingStepUp('screen.action', { id: 'a1' });
    let finish: () => void = () => undefined;
    const resume = jest.fn(
      () =>
        new Promise<void>((resolve) => {
          finish = resolve;
        })
    );

    const { result, rerender } = renderHook(() => useResumeAfterStepUp<{ id: string }>('screen.action', resume));

    await waitFor(() => expect(result.current).toBe(true));
    expect(resume).toHaveBeenCalledWith({ id: 'a1' });
    finish();
    await waitFor(() => expect(result.current).toBe(false));
    rerender();
    expect(resume).toHaveBeenCalledTimes(1);
    expect(peekPendingStepUp('screen.action')).toBeNull();
  });

  it('does nothing when no action was remembered or it has expired', () => {
    savePendingStepUp('screen.action', {}, Date.now() - stepUpTtlMs - 1);
    const resume = jest.fn();

    const { result } = renderHook(() => useResumeAfterStepUp('screen.action', resume));

    expect(resume).not.toHaveBeenCalled();
    expect(result.current).toBe(false);
  });

  it('waits until it is enabled before using the remembered action up', async () => {
    savePendingStepUp('screen.action', { id: 'a1' });
    const resume = jest.fn();

    const { result, rerender } = renderHook(({ enabled }) => useResumeAfterStepUp('screen.action', resume, enabled), {
      initialProps: { enabled: false },
    });
    expect(resume).not.toHaveBeenCalled();
    expect(peekPendingStepUp('screen.action')).not.toBeNull();

    rerender({ enabled: true });
    expect(resume).toHaveBeenCalledTimes(1);
    await waitFor(() => expect(result.current).toBe(false));
  });

  it('survives a resume that throws', async () => {
    savePendingStepUp('screen.action', {});
    const { result } = renderHook(() =>
      useResumeAfterStepUp('screen.action', async () => {
        throw new Error('boom');
      })
    );

    await waitFor(() => expect(result.current).toBe(false));
  });
});
