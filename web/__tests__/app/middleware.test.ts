import { contentSecurityPolicy } from '../../lib/content-security-policy';

describe('contentSecurityPolicy', () => {
  it('allows Microsoft authorization after client-side navigation to Key Vault administration', () => {
    const policy = contentSecurityPolicy('nonce');

    expect(policy).toContain("connect-src 'self' https://login.microsoftonline.com");
  });

  it('allows only the hosted Razorpay checkout frames needed for payment entry', () => {
    const policy = contentSecurityPolicy('nonce');

    expect(policy).toContain(
      "frame-src 'self' https://login.microsoftonline.com https://checkout.razorpay.com https://api.razorpay.com"
    );
    expect(policy).toContain("frame-ancestors 'none'");
  });
});