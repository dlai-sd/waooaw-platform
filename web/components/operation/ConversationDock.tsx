'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R028, R029, R030, R031
// Constitutional basis: C-001, C-023, C-042, C-049, C-059, C-063

import { useState } from 'react';
import {
  operationApi,
  problemText,
  type ChatAllowance,
  type NextStep,
  type OperationRoute,
} from '@/lib/agent-operation';
import type { OperationMessages } from '@/lib/operation-i18n';

type Props = {
  relationshipId: string;
  next: NextStep | null;
  readinessLine: string;
  chats: ChatAllowance;
  copy: OperationMessages;
  stopped: boolean;
  onAct: (step: NextStep, route: OperationRoute) => void;
  onChats: (chats: ChatAllowance) => void;
};

// The agent beside the customer in every mode and view. It opens with the one next step, the same words as the readiness
// line, and offers "Do it for me", "Let me do it" and "Explain". The platform conversation itself lives in the shell's
// dock; this panel only guides, and both routes call the same commands.
export function ConversationDock({ relationshipId, next, readinessLine, chats, copy, stopped, onAct, onChats }: Props) {
  const [explaining, setExplaining] = useState(false);
  const [message, setMessage] = useState('');

  async function doItForMe(step: NextStep) {
    const counted = await operationApi.recordChat(relationshipId);
    if (!counted.ok) {
      setMessage(
        counted.problem.code === 'OPERATION_CHAT_ALLOWANCE_REACHED' ? copy.chatLimit : problemText(counted.problem)
      );
      return;
    }
    setMessage('');
    onChats(counted.data);
    onAct(step, 'ASKED');
  }

  function openConversation() {
    window.dispatchEvent(new CustomEvent('waooaw:open-conversation'));
  }

  return (
    <aside aria-label={copy.conversationLabel} className="op-dock">
      <h2>{copy.conversationLabel}</h2>
      <p className="op-dock-budget">
        <strong>{chats.remaining}</strong> {copy.chatsLeft}
      </p>
      {stopped ? <p role="alert">{copy.stoppedBanner}</p> : null}
      <p className="op-dock-step">
        <span className="section-label">{copy.nextStep}</span>
        <br />
        {next ? next.text : copy.allDone}
      </p>
      {next ? (
        <div className="op-dock-actions">
          <button className="primary-command" onClick={() => onAct(next, 'TOOL')} type="button">
            {next.primaryLabel}
          </button>
          <button
            className="secondary-link"
            disabled={chats.reached || stopped}
            onClick={() => void doItForMe(next)}
            type="button"
          >
            {copy.doItForMe}
          </button>
          <button className="secondary-link" onClick={() => onAct(next, 'TOOL')} type="button">
            {copy.letMeDoIt}
          </button>
          <button
            aria-expanded={explaining}
            className="secondary-link"
            onClick={() => setExplaining(!explaining)}
            type="button"
          >
            {copy.explain}
          </button>
        </div>
      ) : null}
      {explaining ? (
        <p className="op-dock-explain">
          {copy.readiness}: {readinessLine}
        </p>
      ) : null}
      {chats.reached ? <output>{copy.chatLimit}</output> : null}
      <button className="secondary-link" onClick={openConversation} type="button">
        {copy.askPlaceholder}
      </button>
      <output aria-live="polite">{message}</output>
    </aside>
  );
}
