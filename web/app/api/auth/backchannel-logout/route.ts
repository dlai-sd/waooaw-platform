import { NextResponse, type NextRequest } from 'next/server';
import { validateBackchannelLogout } from '@/lib/backchannel-logout';
import { applyBackchannelLogout } from '@/lib/web-session-store';

export async function POST(request: NextRequest) {
  try {
    if (!request.headers.get('content-type')?.startsWith('application/x-www-form-urlencoded'))
      throw new Error('Unsupported logout media type');
    const form = await request.formData();
    const compactToken = form.get('logout_token');
    if (typeof compactToken !== 'string' || compactToken.length > 16_384) throw new Error('Logout token is absent');
    const logout = await validateBackchannelLogout(compactToken);
    const outcome = await applyBackchannelLogout(logout);
    if (outcome === 'REPLAY') throw new Error('Logout token was replayed');
    return new NextResponse(null, {
      status: 204,
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch {
    return NextResponse.json(
      { code: 'IDENTITY_LOGOUT_REJECTED' },
      { status: 400, headers: { 'Cache-Control': 'no-store' } }
    );
  }
}
