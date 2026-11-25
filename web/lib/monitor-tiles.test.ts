// Implements: work-contracts/WC-170-real-agent-work-end-to-end.md WC170-R011
// Constitutional basis: C-049, C-059, C-076

import { groupTiles, isStale, tileGroup } from './monitor-tiles';

describe('monitor tiles', () => {
  it('groups by what the measure is built from: outcomes, then performance, then technical telemetry', () => {
    expect(tileGroup('Customer Confirmation')).toBe('OUTCOME');
    expect(tileGroup('Public Observation')).toBe('OUTCOME');
    expect(tileGroup('Platform Owner Record')).toBe('PERFORMANCE');
    expect(tileGroup('agent')).toBe('PERFORMANCE');
    expect(tileGroup('System Telemetry')).toBe('TECHNICAL');
  });

  it('keeps every tile in exactly one group and keeps their order', () => {
    const tiles = [
      { tileId: 'a', owner: 'System Telemetry', freshness: 'CURRENT' },
      { tileId: 'b', owner: 'Customer Confirmation', freshness: 'CURRENT' },
      { tileId: 'c', owner: 'Platform Owner Record', freshness: 'CURRENT' },
      { tileId: 'd', owner: 'Public Observation', freshness: 'STALE' },
    ];
    const groups = groupTiles(tiles);
    expect(groups.OUTCOME.map((tile) => tile.tileId)).toEqual(['b', 'd']);
    expect(groups.PERFORMANCE.map((tile) => tile.tileId)).toEqual(['c']);
    expect(groups.TECHNICAL.map((tile) => tile.tileId)).toEqual(['a']);
  });

  it('treats anything that is not current as stale', () => {
    expect(isStale('CURRENT')).toBe(false);
    expect(isStale('STALE')).toBe(true);
    expect(isStale('UNAVAILABLE')).toBe(true);
  });
});
