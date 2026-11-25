// Implements: architecture/reference/product/ae02-real-work-solution-contract.md DC-7 Monitor projection (WC170-R011)
// Constitutional basis: C-049, C-059, C-063

export type TileGroup = 'OUTCOME' | 'PERFORMANCE' | 'TECHNICAL';

type TileLike = { tileId: string; owner: string; freshness: string };

// The owner label is the declared evidence source in plain words, so the group follows what the measure is built from.
export function tileGroup(owner: string): TileGroup {
  const text = owner.toLowerCase();
  if (text.includes('telemetry')) return 'TECHNICAL';
  if (text.includes('customer confirmation') || text.includes('public observation')) return 'OUTCOME';
  return 'PERFORMANCE';
}

// A figure that is not current is marked stale and never presented as a current number.
export const isStale = (freshness: string) => freshness !== 'CURRENT';

export function groupTiles<T extends TileLike>(tiles: readonly T[]): Record<TileGroup, T[]> {
  const groups: Record<TileGroup, T[]> = { OUTCOME: [], PERFORMANCE: [], TECHNICAL: [] };
  for (const tile of tiles) groups[tileGroup(tile.owner)].push(tile);
  return groups;
}
