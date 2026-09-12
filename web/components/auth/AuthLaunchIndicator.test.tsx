import { render, screen } from '@testing-library/react';
import { usePathname } from 'next/navigation';
import { AuthLaunchIndicator } from './AuthLaunchIndicator';
import { useAuthJourney } from './AuthJourney';

jest.mock('next/navigation', () => ({ usePathname: jest.fn(), useRouter: () => ({ replace: jest.fn() }) }));
jest.mock('./AuthJourney', () => ({ useAuthJourney: jest.fn() }));

describe('AuthLaunchIndicator', () => {
  beforeAll(() => {
    HTMLDialogElement.prototype.showModal = function showModal() { this.setAttribute('open', ''); };
    HTMLDialogElement.prototype.close = function close() { this.removeAttribute('open'); };
  });

  beforeEach(() => {
    jest.mocked(useAuthJourney).mockReturnValue({
      current: { origin: '/', trigger: null },
      launching: true,
      cancelLaunch: jest.fn(),
      completeLaunch: jest.fn(),
    });
  });

  it('shows the loading dialog while the public route still owns the transition', () => {
    jest.mocked(usePathname).mockReturnValue('/');
    render(<AuthLaunchIndicator />);

    expect(screen.getByRole('dialog', { name: 'Loading' })).toBeVisible();
  });

  it.each(['/login', '/register'])('does not overlap the resolved %s route dialog', (pathname) => {
    jest.mocked(usePathname).mockReturnValue(pathname);
    render(<AuthLaunchIndicator />);

    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });
});