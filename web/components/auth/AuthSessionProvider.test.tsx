import { render, screen } from '@testing-library/react';
import { AuthSessionProvider } from './AuthSessionProvider';

const mockSessionProvider = jest.fn(({ children }: { children: React.ReactNode }) => <>{children}</>);

jest.mock('next-auth/react', () => ({
  SessionProvider: (properties: { children: React.ReactNode; refetchInterval: number }) =>
    mockSessionProvider(properties),
}));

describe('AuthSessionProvider', () => {
  it('refreshes the brokered session every five minutes', () => {
    render(
      <AuthSessionProvider>
        <span>Protected content</span>
      </AuthSessionProvider>
    );

    expect(screen.getByText('Protected content')).toBeInTheDocument();
    expect(mockSessionProvider).toHaveBeenCalledWith(expect.objectContaining({ refetchInterval: 300 }));
  });
});
