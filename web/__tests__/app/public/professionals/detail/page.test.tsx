import { render, screen } from '@testing-library/react';
import ProfessionalPage from '@/app/(public)/professionals/[slug]/page';

jest.mock('next/navigation', () => ({ notFound: jest.fn() }));
jest.mock('@/components/public/StructuredData', () => ({ StructuredData: () => null }));

it.each([
  ['Start trial', 'trial'],
  ['Hire', 'hire'],
])('preserves the professional and %s intent through registration', async (label, intent) => {
  render(await ProfessionalPage({ params: Promise.resolve({ slug: 'digital-marketing' }) }));

  const href = screen.getByRole('link', { name: label }).getAttribute('href');
  const registrationUrl = new URL(href!, 'https://waooaw.test');

  expect(registrationUrl.pathname).toBe('/register');
  expect(registrationUrl.searchParams.get('returnTo')).toBe(
    `/marketplace?professionalType=DIGITAL_MARKETING&version=3.1.0&intent=${intent}`,
  );
});