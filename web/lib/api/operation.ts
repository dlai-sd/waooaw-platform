import 'server-only';

// Implements: work-contracts/WC-174-agent-operation-modes-calendar-and-dma-journey.md WC174-R002, R003
// Constitutional basis: C-001, C-023, C-059, C-063

import type { OperationFrame } from '@/lib/agent-operation';
import { logServerFailure } from '@/lib/server-failure';

const businessPlatformUrl = process.env.BUSINESS_PLATFORM_URL ?? 'http://localhost:5001';

// Never throws: a disabled flag, an agent without modes or an unreachable service each mean "show the workbench".
export async function getOperationFrame(relationshipId: string, accessToken: string): Promise<OperationFrame | null> {
  try {
    const response = await fetch(
      `${businessPlatformUrl}/api/v1/employment/relationships/${relationshipId}/operation/frame`,
      {
        headers: { Accept: 'application/json', Authorization: `Bearer ${accessToken}` },
        cache: 'no-store',
      }
    );
    if (!response.ok) return null;
    const frame = (await response.json()) as OperationFrame;
    return frame.modesDeclared && frame.modes.length > 0 ? frame : null;
  } catch (error) {
    logServerFailure('web.api.operation.frame_failed', error);
    return null;
  }
}
