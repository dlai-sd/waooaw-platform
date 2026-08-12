import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { VoiceContribution } from './VoiceContribution';

const relationshipId = '5f33925b-fb0c-4366-8414-7f85309639b9';

class RecorderMock {
  static isTypeSupported = () => true;
  static latest: RecorderMock;
  state: RecordingState = 'inactive';
  mimeType = 'audio/webm';
  ondataavailable: ((event: BlobEvent) => void) | null = null;
  onstop: (() => void) | null = null;

  constructor() { RecorderMock.latest = this; }
  start() { this.state = 'recording'; }
  pause() { this.state = 'paused'; }
  resume() { this.state = 'recording'; }
  stop() {
    this.state = 'inactive';
    this.ondataavailable?.({ data: new Blob(['voice'], { type: this.mimeType }) } as BlobEvent);
    this.onstop?.();
  }
}

const textFallbackId = 'text-fallback';

function renderVoice(stopped = false) {
  return render(<><textarea id={textFallbackId} /><VoiceContribution relationshipId={relationshipId} relationshipStopped={stopped} textFallbackId={textFallbackId} /></>);
}

function jsonResponse(body: unknown, status: number) {
  return { ok: status >= 200 && status < 300, status, json: async () => body } as Response;
}

async function startAndStop() {
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Record' }));
  await screen.findByRole('button', { name: 'Stop' });
  fireEvent.click(screen.getByRole('button', { name: 'Stop' }));
  await screen.findByRole('button', { name: 'Upload for transcript' });
}

beforeEach(() => {
  Object.defineProperty(globalThis.crypto, 'randomUUID', { configurable: true, value: jest.fn(() => '33333333-3333-4333-8333-333333333333') });
  Object.defineProperty(global, 'MediaRecorder', { configurable: true, value: RecorderMock });
  Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: jest.fn(() => 'blob:test') });
  Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: jest.fn() });
  Object.defineProperty(navigator, 'onLine', { configurable: true, value: true });
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: { getUserMedia: jest.fn(async () => ({ getTracks: () => [{ stop: jest.fn() }] })) },
  });
});

it('returns focus to text when microphone permission is denied', async () => {
  navigator.mediaDevices.getUserMedia = jest.fn(async () => { throw new DOMException('Permission denied', 'NotAllowedError'); });
  renderVoice();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Record' }));

  await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent('Permission denied'));
  expect(document.activeElement).toBe(document.getElementById(textFallbackId));
});

it('never sends until transcript review and explicit send', async () => {
  const fetchMock = jest.fn()
    .mockResolvedValueOnce(jsonResponse({ sessionId: '11111111-1111-1111-1111-111111111111' }, 201))
    .mockResolvedValueOnce(jsonResponse({ state: 'TRANSCRIBING' }, 202))
    .mockResolvedValueOnce(jsonResponse({
      schemaVersion: '1.0.0', sessionId: '11111111-1111-1111-1111-111111111111', state: 'REVIEW_REQUIRED',
      locale: 'en-IN', confidenceBand: 'REVIEW', text: 'review me', version: 1,
    }, 200))
    .mockResolvedValueOnce(jsonResponse({ version: 2 }, 200))
    .mockResolvedValueOnce(jsonResponse({ state: 'RECORDED', evidenceReference: '22222222-2222-2222-2222-222222222222' }, 200));
  global.fetch = fetchMock;
  renderVoice();

  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Record' }));
  await screen.findByRole('button', { name: 'Stop' });
  fireEvent.click(screen.getByRole('button', { name: 'Stop' }));
  fireEvent.click(await screen.findByRole('button', { name: 'Upload for transcript' }));

  const send = await screen.findByRole('button', { name: 'Send voice contribution' });
  expect(send).toBeDisabled();
  expect(fetchMock).toHaveBeenCalledTimes(3);
  fireEvent.click(screen.getByRole('button', { name: 'Confirm correction' }));
  await waitFor(() => expect(send).toBeEnabled());
  expect(fetchMock).toHaveBeenCalledTimes(4);
  fireEvent.click(send);
  await screen.findByRole('button', { name: 'Recorded' });
  expect(fetchMock).toHaveBeenCalledTimes(5);
});

it('keeps text fallback available while Stop disables recording', () => {
  renderVoice(true);
  fireEvent.click(screen.getByRole('checkbox'));
  expect(screen.getByRole('button', { name: 'Record' })).toBeDisabled();
  fireEvent.click(screen.getByRole('button', { name: 'Use text instead' }));
  expect(document.activeElement).toBe(document.getElementById(textFallbackId));
});

it('supports pause, resume, timer progress, and active Stop', async () => {
  jest.useFakeTimers();
  global.fetch = jest.fn().mockResolvedValue(jsonResponse({ sessionId: '11111111-1111-1111-1111-111111111111' }, 201));
  const view = renderVoice();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Record' }));
  await screen.findByRole('button', { name: 'Pause' });
  fireEvent.click(screen.getByRole('button', { name: 'Pause' }));
  expect(screen.getByRole('button', { name: 'Resume' })).toBeVisible();
  fireEvent.click(screen.getByRole('button', { name: 'Resume' }));
  act(() => jest.advanceTimersByTime(2000));
  expect(screen.getByLabelText(/Recording duration 0:02/)).toBeVisible();
  view.rerender(<><textarea id={textFallbackId} /><VoiceContribution relationshipId={relationshipId} relationshipStopped textFallbackId={textFallbackId} /></>);
  await screen.findByText(/Emergency Stop is active/);
  expect(RecorderMock.latest.state).toBe('inactive');
  jest.useRealTimers();
});

it('cancels an active recording without resurrecting playback', async () => {
  const fetchMock = jest.fn()
    .mockResolvedValueOnce(jsonResponse({ sessionId: '11111111-1111-1111-1111-111111111111' }, 201))
    .mockResolvedValueOnce(jsonResponse({ state: 'CANCELLED' }, 200));
  global.fetch = fetchMock;
  renderVoice();
  fireEvent.click(screen.getByRole('checkbox'));
  fireEvent.click(screen.getByRole('button', { name: 'Record' }));
  await screen.findByRole('button', { name: 'Cancel draft' });
  fireEvent.click(screen.getByRole('button', { name: 'Cancel draft' }));

  await waitFor(() => expect(screen.getByText('idle')).toBeVisible());
  expect(screen.queryByRole('button', { name: 'Upload for transcript' })).not.toBeInTheDocument();
  expect(fetchMock).toHaveBeenCalledTimes(2);
});

it('retains the page-local draft while offline and retries with the same audio', async () => {
  global.fetch = jest.fn().mockResolvedValueOnce(jsonResponse({ sessionId: '11111111-1111-1111-1111-111111111111' }, 201));
  renderVoice();
  await startAndStop();
  Object.defineProperty(navigator, 'onLine', { configurable: true, value: false });
  fireEvent.click(screen.getByRole('button', { name: 'Upload for transcript' }));

  await screen.findByText(/offline/);
  expect(screen.getByRole('button', { name: 'Reconcile or retry' })).toBeVisible();
  expect(screen.getByText(/Audio playback is unavailable/)).toBeInTheDocument();
});

it('reports upload and transcript failures without enabling send', async () => {
  const fetchMock = jest.fn()
    .mockResolvedValueOnce(jsonResponse({ sessionId: '11111111-1111-1111-1111-111111111111' }, 201))
    .mockResolvedValueOnce(jsonResponse({ title: 'Media could not be accepted.' }, 415));
  global.fetch = fetchMock;
  renderVoice();
  await startAndStop();
  fireEvent.click(screen.getByRole('button', { name: 'Upload for transcript' }));
  await screen.findByText('Media could not be accepted.');

  fetchMock.mockResolvedValueOnce(jsonResponse({ state: 'TRANSCRIBING' }, 202));
  fetchMock.mockResolvedValueOnce(jsonResponse({
    schemaVersion: '1.0.0', sessionId: '11111111-1111-1111-1111-111111111111', state: 'TRANSCRIBING',
    locale: 'en-IN', confidenceBand: 'UNAVAILABLE', version: 1,
  }, 200));
  fireEvent.click(screen.getByRole('button', { name: 'Reconcile or retry' }));
  await screen.findByText(/Transcription is not ready/);
  expect(screen.queryByRole('button', { name: 'Send voice contribution' })).not.toBeInTheDocument();
});

it('keeps low-confidence send disabled when correction fails', async () => {
  const fetchMock = jest.fn()
    .mockResolvedValueOnce(jsonResponse({ sessionId: '11111111-1111-1111-1111-111111111111' }, 201))
    .mockResolvedValueOnce(jsonResponse({ state: 'TRANSCRIBING' }, 202))
    .mockResolvedValueOnce(jsonResponse({
      schemaVersion: '1.0.0', sessionId: '11111111-1111-1111-1111-111111111111', state: 'REVIEW_REQUIRED',
      locale: 'en-IN', confidenceBand: 'LOW', text: 'uncertain', version: 1,
    }, 200))
    .mockResolvedValueOnce(jsonResponse({ title: 'Transcript version changed.' }, 409));
  global.fetch = fetchMock;
  renderVoice();
  await startAndStop();
  fireEvent.click(screen.getByRole('button', { name: 'Upload for transcript' }));
  const send = await screen.findByRole('button', { name: 'Send voice contribution' });
  fireEvent.click(screen.getByRole('button', { name: 'Confirm correction' }));

  await screen.findByText('Transcript version changed.');
  expect(send).toBeDisabled();
});

it('requires recorded evidence and reports failed or unresolved sends', async () => {
  const fetchMock = jest.fn()
    .mockResolvedValueOnce(jsonResponse({ sessionId: '11111111-1111-1111-1111-111111111111' }, 201))
    .mockResolvedValueOnce(jsonResponse({ state: 'TRANSCRIBING' }, 202))
    .mockResolvedValueOnce(jsonResponse({
      schemaVersion: '1.0.0', sessionId: '11111111-1111-1111-1111-111111111111', state: 'READY_TO_SEND',
      locale: 'en-IN', confidenceBand: 'HIGH', text: 'confirmed', version: 1,
    }, 200))
    .mockResolvedValueOnce(jsonResponse({ state: 'UNKNOWN' }, 200));
  global.fetch = fetchMock;
  renderVoice();
  await startAndStop();
  fireEvent.click(screen.getByRole('button', { name: 'Upload for transcript' }));
  const send = await screen.findByRole('button', { name: 'Send voice contribution' });
  expect(send).toBeEnabled();
  fireEvent.click(send);

  await screen.findByText(/Send outcome needs reconciliation/);
  expect(screen.queryByRole('button', { name: 'Recorded' })).not.toBeInTheDocument();
});