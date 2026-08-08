import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: 'WAOOAW Employment Workspace',
    short_name: 'WAOOAW',
    description: 'Employ and govern WAOOAW digital professionals.',
    start_url: '/',
    display: 'standalone',
    background_color: '#f6f9fc',
    theme_color: '#17334e',
    icons: [
      {
        src: '/icon',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'any',
      },
      {
        src: '/icon',
        sizes: '512x512',
        type: 'image/png',
        purpose: 'maskable',
      },
    ],
  };
}