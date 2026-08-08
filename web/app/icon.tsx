import { ImageResponse } from 'next/og';

export const size = { width: 512, height: 512 };
export const contentType = 'image/png';

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          alignItems: 'center',
          background: '#17334e',
          color: '#ffffff',
          display: 'flex',
          fontFamily: 'serif',
          fontSize: 116,
          height: '100%',
          justifyContent: 'center',
          width: '100%',
        }}
      >
        W
      </div>
    ),
    size
  );
}