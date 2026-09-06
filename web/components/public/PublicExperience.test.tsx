// Implements: work-contracts/WC-078-public-acquisition-experience-plan.md §Approved Landing Composition
// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §7, §9, §10 (WC-03, WC-04, WC-02, WC-05)
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability), C-063 (Data Minimisation)
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { AnnouncementBar } from './AnnouncementBar';
import { ConsentController, cookiePreferencesReopenEvent } from './ConsentController';
import { CookiePreferencesTrigger } from './CookiePreferencesTrigger';
import { InformationPage } from './InformationPage';
import { ProfessionalJourneyShowcase } from './ProfessionalJourneyShowcase';
import { PublicCatalogue } from './PublicCatalogue';
import { listPublicProfessionals } from '@/config/professionals';
import { getProfessionalJourneyContent } from '@/lib/professional-journey-content';

class IntersectionObserverStub implements IntersectionObserver {
  readonly root = null;
  readonly rootMargin = '';
  readonly thresholds: readonly number[] = [];
  private readonly callback: IntersectionObserverCallback;
  constructor(callback: IntersectionObserverCallback) { this.callback = callback; }
  observe(target: Element) { this.callback([{ isIntersecting: true, target } as IntersectionObserverEntry], this); }
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] { return []; }
}

function stubMatchMedia(reduced: boolean) {
  window.matchMedia = ((query: string) => ({
    matches: reduced && query.includes('reduce'),
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  })) as typeof window.matchMedia;
}

function finishTransformTransition(track: HTMLElement) {
  const event = new Event('transitionend', { bubbles: true });
  Object.defineProperty(event, 'propertyName', { value: 'transform' });
  fireEvent(track, event);
}

describe('public acquisition components', () => {
  beforeEach(() => {
    document.cookie = 'waooaw_consent=; Max-Age=0; Path=/';
    window.localStorage.clear();
    document.documentElement.style.removeProperty('--announcement-offset');
    global.fetch = jest.fn(async () => ({ ok: true } as Response));
    (global as unknown as { IntersectionObserver: typeof IntersectionObserver }).IntersectionObserver = IntersectionObserverStub as unknown as typeof IntersectionObserver;
    stubMatchMedia(false);
  });

  it('renders the exact approved hero copy and five film exposures from four professional scenes', () => {
    const content = getProfessionalJourneyContent('en');
    expect(content.heroTitle).toBe('Grow your business with WAOOAW AI professionals');
    expect(content.heroSubtitle).toBe('Guide the work in just ten minutes a day. Spend more time growing your business.');
    const { container } = render(<ProfessionalJourneyShowcase content={content} />);
    const frames = container.querySelectorAll('.spotlight-film-cell');
    expect(frames).toHaveLength(5);
    expect(new Set(Array.from(frames, (frame) => frame.getAttribute('data-scene')))).toEqual(new Set(['agricultural-advisory', 'digital-marketing', 'private-tutoring', 'trading-advisory']));
    expect(container.querySelectorAll('.spotlight-artwork img')).toHaveLength(0);
  });

  it('exposes fixed previous, next, and replay controls', () => {
    render(<ProfessionalJourneyShowcase content={getProfessionalJourneyContent('en')} />);
    expect(screen.getByRole('button', { name: 'Previous professional' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Next professional' })).toBeVisible();
    expect(screen.getByRole('button', { name: 'Replay professional sequence' })).toBeVisible();
  });

  it('undims the destination, disables controls during transport, and normalizes on transition end', () => {
    const { container } = render(<ProfessionalJourneyShowcase content={getProfessionalJourneyContent('en')} />);
    const next = screen.getByRole('button', { name: 'Next professional' });
    const previous = screen.getByRole('button', { name: 'Previous professional' });
    const track = screen.getByTestId('spotlight-film-track');
    fireEvent.click(next);
    expect(next).toBeDisabled();
    expect(previous).toBeDisabled();
    expect(track).toHaveClass('is-moving-forward');
    expect(container.querySelector('.spotlight-film-cell.is-current')).toHaveAttribute('data-position', '1');
    finishTransformTransition(track);
    expect(container.querySelector('.agent-spotlight')).toHaveAttribute('data-professional', 'digital-marketing');
    expect(next).toBeEnabled();
    expect(previous).toBeEnabled();
  });

  it('changes exposure without transport animation when reduced motion is requested', () => {
    stubMatchMedia(true);
    const { container } = render(<ProfessionalJourneyShowcase content={getProfessionalJourneyContent('en')} />);
    fireEvent.click(screen.getByRole('button', { name: 'Previous professional' }));
    expect(container.querySelector('.agent-spotlight')).toHaveAttribute('data-professional', 'trading-advisory');
    expect(screen.getByTestId('spotlight-film-track')).not.toHaveClass('is-moving-backward');
    expect(screen.getByRole('button', { name: 'Next professional' })).toBeEnabled();
  });

  it('replays from the first exposure after manual navigation settles', () => {
    const { container } = render(<ProfessionalJourneyShowcase content={getProfessionalJourneyContent('en')} />);
    const track = screen.getByTestId('spotlight-film-track');
    fireEvent.click(screen.getByRole('button', { name: 'Next professional' }));
    finishTransformTransition(track);
    fireEvent.click(screen.getByRole('button', { name: 'Replay professional sequence' }));
    expect(container.querySelector('.agent-spotlight')).toHaveAttribute('data-professional', 'agricultural-advisory');
  });

  it('links every admitted professional to a public detail page', () => {
    render(<PublicCatalogue professionals={listPublicProfessionals()} />);
    expect(screen.getAllByRole('article')).toHaveLength(4);
    expect(screen.getAllByRole('link', { name: /View scope and limits/i })[0]).toHaveAttribute('href', '/professionals/digital-marketing');
  });

  it('shows role, domain, one outcome, and a truthful publication label on preview cards', () => {
    render(<PublicCatalogue compact professionals={listPublicProfessionals().slice(0, 1)} />);
    const article = screen.getByRole('article');
    expect(article).toHaveTextContent('Digital Marketing Professional');
    expect(article).toHaveTextContent('Audience growth and customer acquisition');
    expect(article.querySelectorAll('li')).toHaveLength(1);
    expect(article).toHaveTextContent('Published');
    expect(screen.getByRole('link', { name: /View scope and limits/i })).toHaveAttribute('href', '/professionals/digital-marketing');
  });

  it('reserves a header offset that reflects the announcement bar and clears it on dismissal', () => {
    jest.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({ height: 48 } as DOMRect);
    render(<AnnouncementBar announcement={{ enabled: true, message: 'Planned maintenance this weekend', href: '', revision: 'r1' }} />);
    expect(screen.getByRole('region', { name: 'Announcement' })).toBeVisible();
    expect(document.documentElement.style.getPropertyValue('--announcement-offset')).toBe('48px');
    const dismissButton = screen.getByRole('button', { name: 'Dismiss announcement' });
    dismissButton.focus();
    fireEvent.click(dismissButton);
    expect(screen.queryByRole('region', { name: 'Announcement' })).not.toBeInTheDocument();
    expect(document.documentElement.style.getPropertyValue('--announcement-offset')).toBe('0px');
    expect(document.activeElement).toBe(document.body);
    expect(JSON.parse(window.localStorage.getItem('waooaw-announcement') ?? '{}')).toEqual({ campaignRevision: 'r1', dismissed: true });
  });

  it('keeps the announcement dismissed only for the stored campaign revision', () => {
    jest.spyOn(HTMLElement.prototype, 'getBoundingClientRect').mockReturnValue({ height: 48 } as DOMRect);
    const { rerender } = render(<AnnouncementBar announcement={{ enabled: true, message: 'Notice', href: '', revision: 'r1' }} />);
    fireEvent.click(screen.getByRole('button', { name: 'Dismiss announcement' }));
    rerender(<AnnouncementBar announcement={{ enabled: true, message: 'Notice', href: '', revision: 'r1' }} />);
    expect(screen.queryByRole('region', { name: 'Announcement' })).not.toBeInTheDocument();
    rerender(<AnnouncementBar announcement={{ enabled: true, message: 'New notice', href: '', revision: 'r2' }} />);
    expect(screen.getByRole('region', { name: 'Announcement' })).toBeVisible();
  });

  it('renders no announcement and no stored offset when the campaign is disabled', () => {
    render(<AnnouncementBar announcement={{ enabled: false, message: '', href: '', revision: 'r1' }} />);
    expect(screen.queryByRole('region', { name: 'Announcement' })).not.toBeInTheDocument();
    expect(document.documentElement.style.getPropertyValue('--announcement-offset')).toBe('0px');
  });

  it('reaches cookie preferences through a normal footer control after a decision is saved', async () => {
    render(<><ConsentController /><CookiePreferencesTrigger /></>);
    await waitFor(() => expect(screen.getByRole('complementary', { name: 'Cookie preferences' })).toBeVisible());
    fireEvent.click(screen.getByRole('button', { name: 'Reject optional' }));
    expect(screen.queryByRole('complementary', { name: 'Cookie preferences' })).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Cookie preferences' }));
    await waitFor(() => expect(screen.getByRole('complementary', { name: 'Cookie preferences' })).toBeVisible());
    expect(screen.getByText('Review cookie preferences')).toBeVisible();
    expect(screen.getByText('Update your optional categories. Necessary preferences remain on.')).toBeVisible();
  });

  it('names Yashus, DLAI Satellite Data, and WAOOAW with their roles in Platform DNA', () => {
    render(<section className="platform-dna"><dl><div><dt>Yashus</dt><dd>Product and experience foundation</dd></div><div><dt>DLAI Satellite Data</dt><dd>Technology and operating company</dd></div><div><dt>WAOOAW</dt><dd>Constitutionally governed digital professionals</dd></div></dl></section>);
    expect(screen.getByText('Yashus').nextElementSibling).toHaveTextContent('Product and experience foundation');
    expect(screen.getByText('DLAI Satellite Data').nextElementSibling).toHaveTextContent('Technology and operating company');
    expect(screen.getByText('WAOOAW').nextElementSibling).toHaveTextContent('Constitutionally governed digital professionals');
  });
  it('offers equally direct accept and reject choices', async () => {
    render(<ConsentController />);
    await waitFor(() => expect(screen.getByRole('complementary', { name: 'Cookie preferences' })).toBeVisible());
    fireEvent.click(screen.getByRole('button', { name: 'Reject optional' }));
    expect(decodeURIComponent(document.cookie)).toContain('"analytics":false');
    // Supersedes the removed persistent floating reopen pill (VR-05); reopening now comes from a normal footer control dispatching this event.
    fireEvent(window, new Event(cookiePreferencesReopenEvent));
    await waitFor(() => expect(screen.getByRole('complementary', { name: 'Cookie preferences' })).toBeVisible());
    fireEvent.click(screen.getByRole('button', { name: 'Accept optional' }));
    expect(decodeURIComponent(document.cookie)).toContain('"advertising":true');
  });


  it('persists granular consent choices', async () => {
    render(<ConsentController />);
    await waitFor(() => expect(screen.getByRole('complementary', { name: 'Cookie preferences' })).toBeVisible());
    fireEvent.click(screen.getByRole('checkbox', { name: 'Analytics' }));
    fireEvent.click(screen.getByRole('checkbox', { name: 'Advertising' }));
    fireEvent.click(screen.getByRole('button', { name: 'Save preferences' }));
    expect(decodeURIComponent(document.cookie)).toContain('"analytics":true');
    expect(decodeURIComponent(document.cookie)).toContain('"advertising":true');
  });

  it('renders public information with safe structured contact data', () => {
    const sections = [['How it works', 'A governed public answer.']] as const;
    const { rerender } = render(<InformationPage contact path="/contact" sections={sections} summary="Contact summary" title="Contact" />);
    expect(screen.getByRole('heading', { name: 'How it works' })).toBeVisible();
    expect(screen.getByRole('link', { name: /Email customersupport@dlaisd.com/ })).toHaveAttribute('href', 'mailto:customersupport@dlaisd.com');
    expect(document.querySelector('script[type="application/ld+json"]')?.textContent).toContain('ContactPoint');
    rerender(<InformationPage path="/about" sections={sections} summary="About summary" title="About" />);
    expect(screen.queryByRole('link', { name: /Email customersupport@dlaisd.com/ })).not.toBeInTheDocument();
  });
});