export function contentSecurityPolicy(nonce: string): string {
  return `default-src 'self'; script-src 'self' 'nonce-${nonce}' 'strict-dynamic'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self' https://login.microsoftonline.com; frame-src 'self' https://login.microsoftonline.com https://checkout.razorpay.com https://api.razorpay.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self'`;
}
