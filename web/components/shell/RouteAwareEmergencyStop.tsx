'use client';

import { usePathname } from 'next/navigation';
import { EmergencyStop } from '@/components/constitutional/EmergencyStop';
import type { StopContext } from './ProtectedAppShell';

export function RouteAwareEmergencyStop({ stopContext }: { stopContext?: StopContext }) {
  const pathname = usePathname();
  const relationshipMatch = pathname.match(/^\/relationships\/([^/]+)(?:\/|$)/);
  const relationshipId = relationshipMatch ? decodeURIComponent(relationshipMatch[1]) : null;
  const contractId = stopContext?.contractId ?? relationshipId;

  return (
    <EmergencyStop
      contractId={contractId}
      activeSessionIds={stopContext?.activeSessionIds ?? []}
    />
  );
}