// Implements: WC-107 R015-R016 authoritative My Agents confirmation handoff
// Constitutional basis: C-023, C-049, C-059, C-063

import { type NextRequest, NextResponse } from 'next/server';
import { consumeMyAgentsSelection, myAgentsSelectionCookie } from '@/lib/api/my-agents-selection';
import { listEmploymentRelationships } from '@/lib/api/relationships';
import { withJourneyTrace } from '@/lib/journey-telemetry';
import { accessTokenFromRequest } from '@/lib/server-auth';

function clearSelectionCookie(response: NextResponse) {
  response.cookies.set(myAgentsSelectionCookie, '', {
    expires: new Date(0),
    httpOnly: true,
    maxAge: 0,
    path: '/professionals/mine',
    sameSite: 'strict',
    secure: true,
  });
  return response;
}

async function resolveSelection(request: NextRequest) {
  const handle = request.cookies.get(myAgentsSelectionCookie)?.value;
  const accessToken = await accessTokenFromRequest(request);
  if (!handle || !accessToken) return clearSelectionCookie(new NextResponse(null, { status: 204 }));
  try {
    const selection = await consumeMyAgentsSelection(accessToken, handle);
    if (!selection) return clearSelectionCookie(new NextResponse(null, { status: 204 }));
    const relationships = await listEmploymentRelationships(accessToken);
    const selected = relationships.items.find((item) => item.relationshipId === selection.relationshipId);
    if (!selected) return clearSelectionCookie(new NextResponse(null, { status: 204 }));

    let confirmation: string | null = null;
    if (
      selection.outcomeKind === 'TRIAL_STARTED' &&
      selected.acquisitionMode === 'TRIAL' &&
      selected.lifecycleState === 'TRIAL_ACTIVE' &&
      selected.trialStatus === 'ACTIVE'
    ) {
      confirmation = 'Trial started';
    } else if (selected.acquisitionMode === 'HIRE' && selection.outcomeKind === 'HIRE_PAID') {
      confirmation = 'Payment confirmed. Professional hired.';
    } else if (selected.acquisitionMode === 'HIRE' && selection.outcomeKind === 'HIRE_ZERO_PRICE') {
      confirmation = 'Professional hired. No payment was due.';
    }
    if (!confirmation) return clearSelectionCookie(new NextResponse(null, { status: 204 }));
    return clearSelectionCookie(
      NextResponse.json(
        {
          relationshipId: selected.relationshipId,
          confirmation,
          nextActionLabel: selected.nextActionLabel,
        },
        { headers: { 'Cache-Control': 'no-store' } }
      )
    );
  } catch {
    return clearSelectionCookie(new NextResponse(null, { status: 204 }));
  }
}

export const POST = (request: NextRequest) =>
  withJourneyTrace('my_agents.selection', () => resolveSelection(request));