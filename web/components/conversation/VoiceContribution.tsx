'use client';

// Implements: WC-062; UX-VOICE-01 through UX-VOICE-12
// Constitutional basis: C-001, C-023, C-042, C-059, C-063

import {
  CircleAlert,
  CircleCheck,
  Mic,
  Pause,
  Play,
  RotateCcw,
  Send,
  Square,
  Trash2,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { VoiceTranscriptV1FromJSON } from '@/lib/api/generated/models/VoiceTranscriptV1';

type CaptureState = 'idle' | 'recording' | 'paused' | 'review' | 'uploading' | 'transcribing' | 'ready' | 'sending' | 'sent' | 'error';

interface VoiceContributionProps {
  relationshipId: string;
  relationshipStopped: boolean;
  textFallbackId: string;
}

async function problemTitle(response: Response) {
  const problem = await response.json().catch(() => undefined) as { title?: unknown } | undefined;
  return typeof problem?.title === 'string' ? problem.title : 'Voice contribution is unavailable. Your text draft is unchanged.';
}

function formatDuration(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`;
}

function supportedMimeType() {
  return ['audio/webm', 'audio/ogg'].find((type) => MediaRecorder.isTypeSupported(type)) ?? '';
}

export function VoiceContribution({ relationshipId, relationshipStopped, textFallbackId }: VoiceContributionProps) {
  const [state, setState] = useState<CaptureState>('idle');
  const [consent, setConsent] = useState(false);
  const [locale, setLocale] = useState('en-IN');
  const [elapsed, setElapsed] = useState(0);
  const [sessionId, setSessionId] = useState('');
  const [audio, setAudio] = useState<Blob>();
  const [audioUrl, setAudioUrl] = useState('');
  const [transcript, setTranscript] = useState('');
  const [version, setVersion] = useState(1);
  const [confidence, setConfidence] = useState('UNAVAILABLE');
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState('');
  const [announcement, setAnnouncement] = useState('');
  const recorder = useRef<MediaRecorder>();
  const stream = useRef<MediaStream>();
  const chunks = useRef<Blob[]>([]);
  const discardOnStop = useRef(false);
  const timer = useRef<ReturnType<typeof setInterval>>();
  const operationKey = useRef<string>();

  function currentOperationKey() {
    operationKey.current ??= crypto.randomUUID();
    return operationKey.current;
  }

  function focusTextFallback() {
    document.getElementById(textFallbackId)?.focus();
  }

  function stopTracks() {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = undefined;
    if (timer.current) clearInterval(timer.current);
    timer.current = undefined;
  }

  useEffect(() => () => {
    stopTracks();
    if (audioUrl) URL.revokeObjectURL(audioUrl);
  }, [audioUrl]);

  useEffect(() => {
    if (!relationshipStopped) return;
    if (recorder.current?.state !== 'inactive') recorder.current?.stop();
    stopTracks();
    setState('error');
    setError('Emergency Stop is active. Voice commands are disabled; your unsent text remains available.');
  }, [relationshipStopped]);

  async function startRecording() {
    if (!consent || relationshipStopped) return;
    setError('');
    try {
      const media = await navigator.mediaDevices.getUserMedia({ audio: true });
      const create = await fetch(`/api/voice/${encodeURIComponent(relationshipId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'create', idempotencyKey: currentOperationKey(), locale }),
      });
      if (!create.ok) throw new Error(await problemTitle(create));
      const created = await create.json() as { sessionId: string };
      setSessionId(created.sessionId);
      stream.current = media;
      chunks.current = [];
      discardOnStop.current = false;
      const mimeType = supportedMimeType();
      const nextRecorder = new MediaRecorder(media, mimeType ? { mimeType } : undefined);
      nextRecorder.ondataavailable = (event) => { if (event.data.size) chunks.current.push(event.data); };
      nextRecorder.onstop = () => {
        if (discardOnStop.current) {
          discardOnStop.current = false;
          stopTracks();
          return;
        }
        const draft = new Blob(chunks.current, { type: nextRecorder.mimeType || 'audio/webm' });
        const nextUrl = URL.createObjectURL(draft);
        setAudio(draft);
        setAudioUrl((current) => { if (current) URL.revokeObjectURL(current); return nextUrl; });
        setState('review');
        setAnnouncement('Recording stopped. Review playback before upload.');
        stopTracks();
      };
      recorder.current = nextRecorder;
      nextRecorder.start(1000);
      setElapsed(0);
      setState('recording');
      timer.current = setInterval(() => setElapsed((current) => {
        if (current >= 179) {
          recorder.current?.stop();
          return 180;
        }
        return current + 1;
      }), 1000);
      setAnnouncement('Recording started. Nothing will be sent automatically.');
    } catch (caught) {
      stopTracks();
      setState('error');
      setError(caught instanceof Error ? caught.message : 'Microphone permission is unavailable. Use the text message field.');
      focusTextFallback();
    }
  }

  function pauseOrResume() {
    if (recorder.current?.state === 'recording') {
      recorder.current.pause();
      setState('paused');
      setAnnouncement('Recording paused.');
    } else if (recorder.current?.state === 'paused') {
      recorder.current.resume();
      setState('recording');
      setAnnouncement('Recording resumed.');
    }
  }

  async function cancelDraft() {
    discardOnStop.current = true;
    if (recorder.current?.state !== 'inactive') recorder.current?.stop();
    stopTracks();
    if (sessionId) {
      await fetch(`/api/voice/${encodeURIComponent(relationshipId)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'cancel', sessionId, idempotencyKey: crypto.randomUUID() }),
      }).catch(() => undefined);
    }
    if (audioUrl) URL.revokeObjectURL(audioUrl);
    setAudio(undefined);
    setAudioUrl('');
    setTranscript('');
    setSessionId('');
    setElapsed(0);
    setState('idle');
    operationKey.current = undefined;
    setAnnouncement('Voice draft cancelled. The text message field remains available.');
  }

  async function fetchTranscript() {
    setState('transcribing');
    const response = await fetch(`/api/voice/${encodeURIComponent(relationshipId)}?sessionId=${encodeURIComponent(sessionId)}&resource=transcript`, { cache: 'no-store' });
    if (!response.ok) throw new Error(await problemTitle(response));
    const result = VoiceTranscriptV1FromJSON(await response.json());
    if (!result.text) throw new Error('Transcription is not ready. Reconcile again or use the text message field.');
    setTranscript(result.text);
    setVersion(result.version);
    setConfidence(result.confidenceBand);
    setConfirmed(result.confidenceBand === 'HIGH');
    setState('ready');
    setAnnouncement(`Transcript ready with ${result.confidenceBand.toLowerCase()} confidence. Review it before sending.`);
  }

  async function upload() {
    if (!audio || !sessionId || !navigator.onLine) {
      setState('error');
      setError('You are offline. The voice draft remains in this page; reconnect before retrying or use text.');
      return;
    }
    setState('uploading');
    setError('');
    const form = new FormData();
    form.set('audio', audio, 'voice-draft');
    form.set('sessionId', sessionId);
    form.set('idempotencyKey', currentOperationKey());
    try {
      const response = await fetch(`/api/voice/${encodeURIComponent(relationshipId)}`, { method: 'POST', body: form });
      if (!response.ok) throw new Error(await problemTitle(response));
      await fetchTranscript();
    } catch (caught) {
      setState('error');
      setError(caught instanceof Error ? caught.message : 'Upload outcome is unknown. Reconcile before retrying.');
    }
  }

  async function confirmCorrection() {
    if (!transcript.trim()) return;
    setError('');
    const response = await fetch(`/api/voice/${encodeURIComponent(relationshipId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'correct', sessionId, idempotencyKey: crypto.randomUUID(), expectedVersion: version, correctedText: transcript.trim() }),
    });
    if (!response.ok) {
      setError(await problemTitle(response));
      return;
    }
    const receipt = await response.json() as { version: number };
    setVersion(receipt.version);
    setConfirmed(true);
    setAnnouncement('Transcript correction confirmed. It has not been sent.');
  }

  async function sendVoice() {
    if (!confirmed || relationshipStopped) return;
    setState('sending');
    const response = await fetch(`/api/voice/${encodeURIComponent(relationshipId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'send', sessionId, idempotencyKey: crypto.randomUUID(), acceptedTranscriptVersion: version }),
    });
    if (!response.ok) {
      setState('error');
      setError(await problemTitle(response));
      return;
    }
    const outcome = await response.json() as { state: string; evidenceReference?: string };
    if (outcome.state !== 'RECORDED' || !outcome.evidenceReference) {
      setState('error');
      setError('Send outcome needs reconciliation. Do not create another contribution.');
      return;
    }
    setState('sent');
    setAnnouncement('Voice contribution recorded with constitutional evidence.');
  }

  const activeCapture = state === 'recording' || state === 'paused';
  return (
    <section className="voice-contribution" aria-labelledby={`voice-title-${relationshipId}`}>
      <div className="voice-heading">
        <div><p className="section-label">Voice draft</p><h3 id={`voice-title-${relationshipId}`}>Record a message</h3></div>
        <span className={`voice-state voice-state-${state}`}>{state.replaceAll('_', ' ')}</span>
      </div>
      <p className="voice-disclosure">Microphone audio is transcribed for review. Nothing is sent until you choose <strong>Send voice contribution</strong>. Maximum 3:00 and 15 MiB.</p>
      <label className="voice-consent"><input checked={consent} disabled={activeCapture || state === 'sent'} onChange={(event) => setConsent(event.target.checked)} type="checkbox" />I agree to record and transcribe this draft.</label>
      <label className="voice-locale">Language<select disabled={state !== 'idle' && state !== 'error'} onChange={(event) => setLocale(event.target.value)} value={locale}><option value="en-IN">English (India)</option><option value="hi-IN">Hindi (India)</option><option value="mr-IN">Marathi (India)</option></select></label>
      <div className="voice-meter" aria-label={`Recording duration ${formatDuration(elapsed)} of 3 minutes`}><span>{formatDuration(elapsed)}</span><progress max={180} value={elapsed} /></div>
      <div className="voice-commands">
        {(state === 'idle' || state === 'error') ? <button disabled={!consent || relationshipStopped} onClick={() => void startRecording()} type="button"><Mic aria-hidden="true" />Record</button> : null}
        {activeCapture ? <button onClick={pauseOrResume} type="button">{state === 'paused' ? <Play aria-hidden="true" /> : <Pause aria-hidden="true" />}{state === 'paused' ? 'Resume' : 'Pause'}</button> : null}
        {activeCapture ? <button onClick={() => recorder.current?.stop()} type="button"><Square aria-hidden="true" />Stop</button> : null}
        {state !== 'idle' && state !== 'sent' ? <button className="voice-delete" onClick={() => void cancelDraft()} type="button"><Trash2 aria-hidden="true" />Cancel draft</button> : null}
        {(state === 'review' || state === 'error') && audio ? <button onClick={() => void upload()} type="button"><RotateCcw aria-hidden="true" />{state === 'review' ? 'Upload for transcript' : 'Reconcile or retry'}</button> : null}
        <button onClick={focusTextFallback} type="button">Use text instead</button>
      </div>
      {audioUrl ? <audio controls preload="metadata" src={audioUrl}>Audio playback is unavailable. Use text instead.</audio> : null}
      {state === 'ready' || state === 'sending' || state === 'sent' ? (
        <div className="voice-review">
          <div className="voice-confidence">{confidence === 'HIGH' ? <CircleCheck aria-hidden="true" /> : <CircleAlert aria-hidden="true" />}Confidence: {confidence.toLowerCase()}</div>
          <label htmlFor={`voice-transcript-${relationshipId}`}>Review transcript</label>
          <textarea disabled={state === 'sending' || state === 'sent'} id={`voice-transcript-${relationshipId}`} onChange={(event) => { setTranscript(event.target.value); setConfirmed(false); }} rows={4} value={transcript} />
          {!confirmed && state !== 'sent' ? <button onClick={() => void confirmCorrection()} type="button">Confirm correction</button> : null}
          <button className="send-command" disabled={!confirmed || state === 'sending' || state === 'sent' || relationshipStopped} onClick={() => void sendVoice()} type="button"><Send aria-hidden="true" />{state === 'sent' ? 'Recorded' : state === 'sending' ? 'Sending' : 'Send voice contribution'}</button>
        </div>
      ) : null}
      {error ? <p className="conversation-error" role="alert">{error}</p> : null}
      <p className="visually-hidden" aria-live="polite" aria-atomic="true">{announcement}</p>
    </section>
  );
}