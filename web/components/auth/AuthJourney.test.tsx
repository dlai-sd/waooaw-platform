import { fireEvent, render, screen } from '@testing-library/react';
import Link from 'next/link';
import { AuthJourney, useAuthJourney } from './AuthJourney';

function Capture() {
  const journey = useAuthJourney();
  return <button onClick={() => { document.title = journey?.current.origin ?? ''; }}>Inspect</button>;
}

describe('auth public origin', () => {
  afterEach(() => window.history.replaceState({}, '', '/'));

  it('retains the original public route across login and register switches', () => {
    window.history.replaceState({}, '', '/professionals');
    render(<AuthJourney><Link href="/login" onClick={(event) => event.preventDefault()}>Log in</Link><Capture /></AuthJourney>);
    fireEvent.click(screen.getByText('Log in'));
    window.history.replaceState({}, '', '/register');
    fireEvent.click(screen.getByText('Log in'));
    fireEvent.click(screen.getByText('Inspect'));
    expect(document.title).toBe('/professionals');
  });

  it('does not capture modified or external navigation', () => {
    window.history.replaceState({}, '', '/professionals');
    render(<AuthJourney><Link href="/login" onClick={(event) => event.preventDefault()}>Log in</Link><a href="https://example.com/login" onClick={(event) => event.preventDefault()}>External</a><Capture /></AuthJourney>);
    fireEvent.click(screen.getByText('Log in'), { ctrlKey: true });
    fireEvent.click(screen.getByText('External'));
    fireEvent.click(screen.getByText('Inspect'));
    expect(document.title).toBe('/');
  });
});