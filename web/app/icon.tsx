import { ImageResponse } from 'next/og';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';

// Implements: architecture/reference/ux/wc-105-authentication-flow-defect-remediation-plan.md AUTH-UI-01
// Constitutional basis: C-059 (Implementation Traceability)

export const size = { width: 512, height: 512 };
export const contentType = 'image/png';
const logo = `data:image/png;base64,${readFileSync(join(process.cwd(), 'public/waooaw-platform-logo.png')).toString('base64')}`;

export default function Icon() {
  return new ImageResponse(
    <div
      style={{
        alignItems: 'center',
        background: '#ffffff',
        display: 'flex',
        height: '100%',
        justifyContent: 'center',
        padding: 36,
        width: '100%',
      }}
    >
      <img alt="" height="440" src={logo} width="440" />
    </div>,
    size
  );
}
