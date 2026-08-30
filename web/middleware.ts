// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Information Architecture
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { withAuth, type NextRequestWithAuth } from 'next-auth/middleware';
import { NextResponse, type NextFetchEvent, type NextRequest } from 'next/server';
import { listPublishedArticles } from '@/config/blogs';
import { listPublicProfessionals } from '@/config/professionals';

const protectedMiddleware = withAuth({});
const professionalSlugs = new Set(listPublicProfessionals().map(({ slug }) => slug));
const articleSlugs = new Set(listPublishedArticles().map(({ slug }) => slug));
const protectedFamilies = new Set(['home', 'relationships', 'settings', 'profile', 'founder']);

function contentSecurityPolicy(nonce: string): string {
	return `default-src 'self'; script-src 'self' 'nonce-${nonce}' 'strict-dynamic'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`;
}

function publicResponse(request: NextRequest, nonce: string): NextResponse {
	const requestHeaders = new Headers(request.headers);
	requestHeaders.set('x-nonce', nonce);
	requestHeaders.set('Content-Security-Policy', contentSecurityPolicy(nonce));
	return NextResponse.next({ request: { headers: requestHeaders } });
}

function secure(response: NextResponse, nonce: string): NextResponse {
	response.headers.set('Content-Security-Policy', contentSecurityPolicy(nonce));
	return response;
}

export default async function middleware(request: NextRequest, event: NextFetchEvent) {
	const nonce = crypto.randomUUID();
	const [, family, slug, extra] = request.nextUrl.pathname.split('/');
	if (family === 'professionals' && slug !== 'mine') {
		if (extra || (slug && !professionalSlugs.has(slug))) return secure(new NextResponse('Not found', { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Robots-Tag': 'noindex, nofollow' } }), nonce);
		return secure(publicResponse(request, nonce), nonce);
	}
	if (family === 'blogs') {
		if (extra || (slug && !articleSlugs.has(slug))) return secure(new NextResponse('Not found', { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Robots-Tag': 'noindex, nofollow' } }), nonce);
		return secure(publicResponse(request, nonce), nonce);
	}
	if (protectedFamilies.has(family)) return secure(await protectedMiddleware(request as NextRequestWithAuth, event) as NextResponse, nonce);
	return secure(publicResponse(request, nonce), nonce);
}

export const config = { matcher: ['/((?!api|_next/static|_next/image|favicon.ico|sw.js|workbox-|manifest.webmanifest).*)'] };