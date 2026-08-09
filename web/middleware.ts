export { default } from 'next-auth/middleware';

// Implements: architecture/reference/ux/hybrid-application-shell.md §Route and Layout Ownership
// Constitutional basis: C-059 (Implementation Traceability)

export const config = { matcher: ['/home/:path*', '/professionals/mine/:path*', '/relationships/:path*', '/settings/:path*', '/profile/:path*', '/founder/:path*'] };