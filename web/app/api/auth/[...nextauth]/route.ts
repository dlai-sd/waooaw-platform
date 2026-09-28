import NextAuth from 'next-auth';
import { authOptions } from '@/lib/auth';
import { withJourneyTrace } from '@/lib/journey-telemetry';

const handler = NextAuth(authOptions);

export const GET = (...args: Parameters<typeof handler>) =>
	withJourneyTrace('identity.login', () => handler(...args));
export const POST = (...args: Parameters<typeof handler>) =>
	withJourneyTrace('identity.login', () => handler(...args));
