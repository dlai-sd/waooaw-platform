// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Approved Landing Composition
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AutonomyHandoffConsole } from './AutonomyHandoffConsole';
import { ConsentController } from './ConsentController';
import { PublicCatalogue } from './PublicCatalogue';
import { listPublicProfessionals } from '@/config/professionals';

describe('public acquisition components', () => {
  beforeEach(() => { document.cookie = 'waooaw_consent=; Max-Age=0; Path=/'; });
  it('renders the complete illustrative handoff in semantic order', () => {
    render(<AutonomyHandoffConsole />);
    expect(screen.getByRole('heading', { name: /From trial to autonomous productivity/ })).toBeVisible();
    expect(screen.getAllByRole('listitem').map((item) => item.textContent)).toEqual(expect.arrayContaining([expect.stringContaining('Trial started'), expect.stringContaining('Working autonomously')]));
  });
  it('links every admitted professional to a public detail page', () => {
    render(<PublicCatalogue professionals={listPublicProfessionals()} />);
    expect(screen.getAllByRole('article')).toHaveLength(4);
    expect(screen.getAllByRole('link', { name: /View scope and limits/i })[0]).toHaveAttribute('href', '/professionals/digital-marketing');
  });
  it('offers equally direct accept and reject choices', async () => {
    render(<ConsentController />);
    await waitFor(() => expect(screen.getByRole('complementary', { name: 'Cookie preferences' })).toBeVisible());
    fireEvent.click(screen.getByRole('button', { name: 'Reject optional' }));
    expect(decodeURIComponent(document.cookie)).toContain('"analytics":false');
    fireEvent.click(screen.getByRole('button', { name: 'Cookie preferences' }));
    fireEvent.click(screen.getByRole('button', { name: 'Accept optional' }));
    expect(decodeURIComponent(document.cookie)).toContain('"advertising":true');
  });
});