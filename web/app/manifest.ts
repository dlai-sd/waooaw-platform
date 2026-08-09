import type { MetadataRoute } from 'next';

export default function manifest(): MetadataRoute.Manifest {
  return {
    id: '/',
    name: 'WAOOAW',
    short_name: 'WAOOAW',
    description: 'Employ and govern constitutionally accountable digital professionals.',
    start_url: '/',
    scope: '/',
    display: 'standalone',
    background_color: '#f7f9fc',
    theme_color: '#1e3352',
    categories: ['business', 'productivity'],
    lang: 'en',
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