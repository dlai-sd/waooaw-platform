'use client';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R005, R006, R007
// Constitutional basis: C-001, C-023, C-042, C-059, C-061, C-063

import { useCallback, useEffect, useState, type FormEvent } from 'react';
import {
  monthGrid,
  monthRange,
  operationApi,
  problemText,
  type CalendarView,
  type DayCell,
  type ItemView,
  type LayerView,
  type PlatformView,
} from '@/lib/agent-operation';
import type { OperationMessages } from '@/lib/operation-i18n';
import { ItemCard } from './ItemCard';

export type CalendarViewName = 'MONTH' | 'WEEK' | 'PLATFORMS' | 'STORYBOARD';

type Props = {
  relationshipId: string;
  year: number;
  month: number;
  today: string;
  view: CalendarViewName;
  platforms: PlatformView[];
  selectedId: string | null;
  onSelect: (item: ItemView | null) => void;
  onLoaded: (calendar: CalendarView) => void;
  onChanged: () => void;
  copy: OperationMessages;
  refreshKey: number;
};

function weekOf(grid: DayCell[][], today: string): DayCell[][] {
  const index = grid.findIndex((week) => week.some((cell) => cell.date === today));
  return [grid[index >= 0 ? index : 0]];
}

function EntryButton({
  entry,
  selected,
  onSelect,
}: { entry: ItemView; selected: boolean; onSelect: (item: ItemView) => void }) {
  return (
    <button
      aria-pressed={selected}
      className={`op-entry op-entry-${entry.kind.toLowerCase()}${entry.isSuggestion ? ' op-entry-suggestion' : ''}`}
      onClick={() => onSelect(entry)}
      type="button"
    >
      {entry.title}
    </button>
  );
}

function LayersPanel({
  relationshipId,
  layers,
  copy,
  onChanged,
}: {
  relationshipId: string;
  layers: LayerView[];
  copy: OperationMessages;
  onChanged: () => void;
}) {
  const [name, setName] = useState('');
  const [message, setMessage] = useState('');

  async function toggle(layer: LayerView) {
    const result = await operationApi.setLayer(relationshipId, layer.layerId, !layer.on);
    if (result.ok) onChanged();
    else setMessage(problemText(result.problem));
  }

  async function add(event: FormEvent) {
    event.preventDefault();
    const result = await operationApi.addLayer(relationshipId, name);
    if (result.ok) {
      setName('');
      onChanged();
    } else {
      setMessage(problemText(result.problem));
    }
  }

  return (
    <fieldset className="op-layers">
      <legend>{copy.layersLabel}</legend>
      {layers.map((layer) => (
        <label key={layer.layerId}>
          <input checked={layer.on} onChange={() => void toggle(layer)} type="checkbox" />
          {layer.label}
          {layer.sensitive ? <small> — {copy.sensitiveNote}</small> : null}
        </label>
      ))}
      <form onSubmit={(event) => void add(event)}>
        <label>
          {copy.layerName}
          <input maxLength={40} onChange={(event) => setName(event.target.value)} required value={name} />
        </label>
        <button className="secondary-link" type="submit">
          {copy.addLayer}
        </button>
      </form>
      <output aria-live="polite">{message}</output>
    </fieldset>
  );
}

// The shared calendar: the home screen of a relationship. Every view reads the same records, so they never disagree.
export function CalendarBlock({
  relationshipId,
  year,
  month,
  today,
  view,
  platforms,
  selectedId,
  onSelect,
  onLoaded,
  onChanged,
  copy,
  refreshKey,
}: Props) {
  const [calendar, setCalendar] = useState<CalendarView | null>(null);
  const [failed, setFailed] = useState(false);
  const [loadedKey, setLoadedKey] = useState('');
  const key = `${year}-${month}-${refreshKey}`;

  const load = useCallback(async () => {
    const range = monthRange(year, month);
    const result = await operationApi.calendar(relationshipId, range.from, range.to);
    if (result.ok) {
      setCalendar(result.data);
      setFailed(false);
      onLoaded(result.data);
    } else {
      setFailed(true);
    }
    setLoadedKey(`${year}-${month}-${refreshKey}`);
  }, [relationshipId, year, month, refreshKey, onLoaded]);

  useEffect(() => {
    void load();
  }, [load]);

  if (failed) {
    return (
      <div role="alert">
        <p>{copy.failed}</p>
        <button className="secondary-link" onClick={() => void load()} type="button">
          {copy.retry}
        </button>
      </div>
    );
  }
  if (calendar === null || loadedKey !== key) return <p aria-busy="true">{copy.loading}</p>;

  const entries = calendar.entries;
  const selected = entries.find((entry) => entry.itemId === selectedId) ?? null;
  const grid = monthGrid(year, month, entries);
  const shown = view === 'WEEK' ? weekOf(grid, today) : grid;
  const dated = [...entries].sort((left, right) => (left.startDate ?? '').localeCompare(right.startDate ?? ''));

  return (
    <section aria-label={copy.viewMonth} className="op-calendar">
      <LayersPanel copy={copy} layers={calendar.layers} onChanged={onChanged} relationshipId={relationshipId} />
      {calendar.limits.length > 0 ? (
        <p className="op-limits">
          <strong>{copy.packageLimits}: </strong>
          {calendar.limits.map((limit) => (
            <span key={limit.componentId}>
              {limit.label}: {limit.known ? `${limit.remaining} ${copy.limitLeft}` : copy.limitUnknown}
              {limit.committed > 0 ? `, ${limit.committed} ${copy.limitScheduled}` : ''}{' '}
            </span>
          ))}
        </p>
      ) : null}
      {view === 'MONTH' || view === 'WEEK' ? (
        <table className="op-grid">
          <caption className="op-sr-only">{copy.viewMonth}</caption>
          <thead>
            <tr>
              {shown[0].map((cell) => (
                <th key={cell.date} scope="col">
                  {new Date(`${cell.date}T00:00:00Z`).toLocaleDateString('en', { weekday: 'short', timeZone: 'UTC' })}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {shown.map((week) => (
              <tr key={week[0].date}>
                {week.map((cell) => (
                  <td
                    aria-current={cell.date === today ? 'date' : undefined}
                    className={cell.inMonth ? '' : 'op-out'}
                    key={cell.date}
                  >
                    <span className="op-day">{cell.day}</span>
                    {cell.entries.map((entry) => (
                      <EntryButton
                        entry={entry}
                        key={entry.itemId}
                        onSelect={onSelect}
                        selected={entry.itemId === selectedId}
                      />
                    ))}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
      {view === 'PLATFORMS' ? (
        <div className="op-lanes">
          {platforms.map((platform) => (
            <section aria-label={platform.label} key={platform.platformId}>
              <h3>{platform.label}</h3>
              <ul>
                {entries
                  .filter((entry) => entry.platformId === platform.platformId)
                  .map((entry) => (
                    <li key={entry.itemId}>
                      <EntryButton entry={entry} onSelect={onSelect} selected={entry.itemId === selectedId} />
                    </li>
                  ))}
              </ul>
            </section>
          ))}
        </div>
      ) : null}
      {view === 'STORYBOARD' ? (
        <ol className="op-storyboard">
          {dated
            .filter((entry) => entry.kind === 'PLAN_NODE' || entry.kind === 'CONTENT')
            .map((entry) => (
              <li key={entry.itemId}>
                <EntryButton entry={entry} onSelect={onSelect} selected={entry.itemId === selectedId} />
              </li>
            ))}
        </ol>
      ) : null}
      <ul aria-label={copy.viewMonth} className="op-list-view">
        {dated.length === 0 ? <li>{copy.nothingYet}</li> : null}
        {dated.map((entry) => (
          <li key={entry.itemId}>
            <EntryButton entry={entry} onSelect={onSelect} selected={entry.itemId === selectedId} />
            {entry.startDate ? <time dateTime={entry.startDate}> {entry.startDate}</time> : null}
          </li>
        ))}
      </ul>
      {selected ? (
        <ItemCard
          copy={copy}
          item={selected}
          key={`${selected.itemId}-${selected.versionNo}`}
          onChanged={(next) => {
            onSelect(next);
            onChanged();
          }}
          relationshipId={relationshipId}
        />
      ) : null}
    </section>
  );
}
