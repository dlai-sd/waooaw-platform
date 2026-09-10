'use client';

import { AuthBoundary } from '@/components/auth/AuthBoundary';

export default function ErrorBoundary({ reset }: { reset: () => void }) {
  return <AuthBoundary failed retry={reset} />;
}