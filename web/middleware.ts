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

export default function middleware(request: NextRequest, event: NextFetchEvent) {
	const [, family, slug, extra] = request.nextUrl.pathname.split('/');
	if (family === 'professionals' && slug !== 'mine') {
		if (extra || (slug && !professionalSlugs.has(slug))) return new NextResponse('Not found', { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Robots-Tag': 'noindex, nofollow' } });
		return NextResponse.next();
	}
	if (family === 'blogs') {
		if (extra || (slug && !articleSlugs.has(slug))) return new NextResponse('Not found', { status: 404, headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Robots-Tag': 'noindex, nofollow' } });
		return NextResponse.next();
	}
	return protectedMiddleware(request as NextRequestWithAuth, event);
}

export const config = { matcher: ['/home/:path*', '/professionals/:path*', '/blogs/:path*', '/relationships/:path*', '/settings/:path*', '/profile/:path*', '/founder/:path*'] };