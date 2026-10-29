// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Public Information Architecture
// Constitutional basis: C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { NextResponse, type NextRequest } from 'next/server';
import { listPublishedArticles } from '@/config/blogs';
import { listPublicProfessionals } from '@/config/professionals';
import { contentSecurityPolicy } from '@/lib/content-security-policy';
import { serverSessionMode } from '@/lib/server-session-mode';

const professionalSlugs = new Set(listPublicProfessionals().map(({ slug }) => slug));
const articleSlugs = new Set(listPublishedArticles().map(({ slug }) => slug));
const protectedFamilies = new Set([
  'home',
  'relationships',
  'marketplace',
  'professionals',
  'alerts',
  'settings',
  'profile',
  'founder',
  'admin',
]);

function publicResponse(request: NextRequest, nonce: string): NextResponse {
  const requestHeaders = new Headers(request.headers);
  requestHeaders.set('x-nonce', nonce);
  requestHeaders.set('Content-Security-Policy', contentSecurityPolicy(nonce));
  return NextResponse.next({ request: { headers: requestHeaders } });
}

// NextAuth splits JWT session cookies above ~4 KB into `<name>.0`, `<name>.1`, ...
const legacySessionCookie = /^(__Secure-)?next-auth\.session-token(\.\d+)?$/;

function legacySessionCookieNames(request: NextRequest): string[] {
  return request.cookies
    .getAll()
    .map(({ name }) => name)
    .filter((name) => legacySessionCookie.test(name));
}

function secure(response: NextResponse, nonce: string, request: NextRequest): NextResponse {
  response.headers.set('Content-Security-Policy', contentSecurityPolicy(nonce));
  if (serverSessionMode() === 'enforced') {
    for (const name of legacySessionCookieNames(request)) {
      response.cookies.set(name, '', {
        expires: new Date(0),
        httpOnly: true,
        path: '/',
        sameSite: 'lax',
        secure: name.startsWith('__Secure-'),
      });
    }
  }
  return response;
}

export default async function middleware(request: NextRequest) {
  const nonce = crypto.randomUUID();
  const [, family, slug, extra] = request.nextUrl.pathname.split('/');
  if (family === 'professionals' && slug !== 'mine') {
    if (extra || (slug && !professionalSlugs.has(slug)))
      return secure(
        new NextResponse('Not found', {
          status: 404,
          headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Robots-Tag': 'noindex, nofollow' },
        }),
        nonce,
        request
      );
    return secure(publicResponse(request, nonce), nonce, request);
  }
  if (family === 'blogs') {
    if (extra || (slug && !articleSlugs.has(slug)))
      return secure(
        new NextResponse('Not found', {
          status: 404,
          headers: { 'Content-Type': 'text/plain; charset=utf-8', 'X-Robots-Tag': 'noindex, nofollow' },
        }),
        nonce,
        request
      );
    return secure(publicResponse(request, nonce), nonce, request);
  }
  if (protectedFamilies.has(family)) {
    const mode = serverSessionMode();
    const hasSession =
      mode === 'enforced' ? request.cookies.has('__Host-waooaw-session') : legacySessionCookieNames(request).length > 0;
    if (!hasSession) return secure(NextResponse.redirect(new URL('/login', request.url)), nonce, request);
    return secure(publicResponse(request, nonce), nonce, request);
  }
  return secure(publicResponse(request, nonce), nonce, request);
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|sw.js|workbox-|manifest.webmanifest).*)'],
};
