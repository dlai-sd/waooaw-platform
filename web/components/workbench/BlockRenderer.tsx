// Implements: work-contracts/WC-136-common-agent-workbench-spend-accounts-and-pricing-engine.md C6-05
// Constitutional basis: C-001, C-042, C-059, C-063, ADR-051

import Link from 'next/link';
import type { ReactNode } from 'react';
import type { WorkbenchBlock } from '@/lib/api/workbench-types';
import { labelFor, type WorkbenchMessages } from '@/lib/workbench-i18n';

const supportedVersion = 1;
const kernelTypes = new Set([
  'TEXT',
  'CHOICES',
  'LIST',
  'LINK',
  'STATUS',
  'METRIC',
  'PLAN',
  'DECISION',
  'FORM',
  'EVIDENCE',
]);
const workbenchReference = /^workbench:([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})$/i;
const trendSymbols: Record<string, string> = { UP: '↑', DOWN: '↓', FLAT: '→' };

type Data = Record<string, unknown>;

function record(value: unknown): Data {
  return value !== null && typeof value === 'object' && !Array.isArray(value) ? (value as Data) : {};
}

function text(value: unknown): string | undefined {
  if (typeof value === 'string') return value.length > 0 ? value : undefined;
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  return undefined;
}

function list(value: unknown): Data[] {
  return Array.isArray(value) ? value.map(record) : [];
}

function dateText(value: unknown): string | undefined {
  const raw = text(value);
  if (!raw) return undefined;
  const parsed = new Date(raw);
  return Number.isNaN(parsed.getTime()) ? raw : parsed.toISOString().slice(0, 10);
}

// A destination is only ever an opaque reference; only the workbench of a relationship resolves to a route.
export function destinationHref(destinationRef: string | undefined): string | null {
  const match = destinationRef ? workbenchReference.exec(destinationRef) : null;
  return match ? `/relationships/${match[1].toLowerCase()}` : null;
}

function Heading({ block }: { block: WorkbenchBlock }) {
  return block.label ? <h4 className="workbench-block-title">{block.label}</h4> : null;
}

function Row({ name, children }: { name: string; children: ReactNode }) {
  return (
    <div>
      <dt>{name}</dt>
      <dd>{children}</dd>
    </div>
  );
}

function renderKernel(block: WorkbenchBlock, copy: WorkbenchMessages): ReactNode {
  const data = record(block.data);
  switch (block.type) {
    case 'TEXT':
      return <p>{text(data.text)}</p>;
    case 'CHOICES':
      return (
        <ul className="workbench-plain-list">
          {list(data.choices).map((choice) => (
            <li key={text(choice.choiceId)}>{text(choice.label)}</li>
          ))}
        </ul>
      );
    case 'LIST':
      return (
        <ul className="workbench-plain-list">
          {list(data.rows).map((row) => (
            <li key={text(row.rowId)}>
              <strong>{text(row.title)}</strong>
              {text(row.description) ? <span> {text(row.description)}</span> : null}
            </li>
          ))}
        </ul>
      );
    case 'LINK': {
      const href = destinationHref(text(data.destinationRef));
      const label = text(data.label) ?? copy.openLink;
      return href ? (
        <Link className="secondary-link" href={href}>
          {label}
        </Link>
      ) : (
        <p>{label}</p>
      );
    }
    case 'STATUS':
      return (
        <dl className="workbench-facts">
          <Row name={copy.toolOverview}>{labelFor(copy.states, text(data.state) ?? '')}</Row>
          <Row name={copy.owner}>{text(data.owner)}</Row>
          <Row name={copy.freshness}>{labelFor(copy.freshnessStates, text(data.freshness) ?? '')}</Row>
        </dl>
      );
    case 'METRIC': {
      const trend = text(data.trend);
      return (
        <dl className="workbench-facts">
          <Row name={block.label ?? copy.toolMonitor}>
            {text(data.value)} {text(data.unit)}
            {trend ? (
              <span aria-label={`${copy.trend}: ${labelFor({}, trend)}`} role="img">
                {' '}
                {trendSymbols[trend] ?? ''}
              </span>
            ) : null}
          </Row>
          {text(data.target) ? <Row name={copy.target}>{text(data.target)}</Row> : null}
          <Row name={copy.freshness}>{labelFor(copy.freshnessStates, text(data.freshness) ?? '')}</Row>
        </dl>
      );
    }
    case 'PLAN':
      return (
        <div>
          <p>
            {copy.plan} {text(data.planVersion)}
          </p>
          <ol className="workbench-plain-list">
            {list(data.milestones).map((item) => (
              <li key={text(item.milestoneId)}>
                <strong>{text(item.title)}</strong> {text(item.dueMeaning)}
              </li>
            ))}
          </ol>
          {list(data.calendar).length > 0 ? (
            <ul className="workbench-plain-list" aria-label={copy.calendar}>
              {list(data.calendar).map((entry) => (
                <li key={`${text(entry.date)}-${text(entry.title)}`}>
                  {dateText(entry.date)} {text(entry.title)}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      );
    case 'DECISION':
      return (
        <dl className="workbench-facts">
          <Row name={copy.toolDecisions}>{text(data.effect)}</Row>
          <Row name={copy.decidedBy}>{text(data.authority)}</Row>
          {text(data.cost) ? <Row name={copy.cost}>{text(data.cost)}</Row> : null}
          {dateText(data.expiresAt) ? <Row name={copy.expires}>{dateText(data.expiresAt)}</Row> : null}
        </dl>
      );
    case 'FORM':
      return (
        <ul className="workbench-plain-list">
          {list(data.fields).map((field) => (
            <li key={text(field.fieldId)}>{text(field.label)}</li>
          ))}
        </ul>
      );
    case 'EVIDENCE':
      return (
        <dl className="workbench-facts">
          <Row name={copy.toolEvidence}>{text(data.summary)}</Row>
          {dateText(data.producedAt) ? <Row name={copy.freshness}>{dateText(data.producedAt)}</Row> : null}
        </dl>
      );
    default:
      return null;
  }
}

function Fallback({ block, copy }: { block: WorkbenchBlock; copy: WorkbenchMessages }) {
  const items = (Array.isArray(block.fallback) ? block.fallback : []).filter((item) =>
    ['TEXT', 'CHOICES', 'LIST', 'LINK'].includes(item.type)
  );
  if (items.length === 0) return <p>{copy.unsupportedBlock}</p>;
  return (
    <>
      {items.map((item, index) => (
        <div key={`${block.id}.${index}`}>{renderKernel({ ...block, type: item.type, data: item.data }, copy)}</div>
      ))}
    </>
  );
}

// A block of an unknown type or a higher version never breaks the page: its declared fallback is shown instead.
export function BlockRenderer({ block, copy }: { block: WorkbenchBlock; copy: WorkbenchMessages }) {
  const renderable = kernelTypes.has(block.type) && block.version <= supportedVersion;
  return (
    <article
      aria-label={block.label}
      className="workbench-block"
      data-block-type={block.type}
      data-sensitivity={block.sensitivity}
    >
      <Heading block={block} />
      {renderable ? renderKernel(block, copy) : <Fallback block={block} copy={copy} />}
    </article>
  );
}
