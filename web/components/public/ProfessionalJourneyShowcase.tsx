// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §7, §9, §10.4
// Implements: prototypes/wc078-agent-spotlight/index.html at 0798a072 (Founder-approved film-reel behavior)
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability), C-063 (Data Minimisation)
'use client';

import { BookOpen, ChartCandlestick, ChevronLeft, ChevronRight, Megaphone, RotateCcw, Sprout } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { listPublicProfessionals } from '@/config/professionals';
import type { ProfessionalJourneyContent } from '@/lib/professional-journey-content';

const AUTO_ADVANCE_MS = 3820;
const SCENE_ORDER = ['agricultural-advisory', 'digital-marketing', 'private-tutoring', 'trading-advisory'] as const;
type SceneId = (typeof SCENE_ORDER)[number];
type Direction = -1 | 1;
type SpotlightScene = Readonly<{ id: SceneId; name: string; context: string; capability: string; outcomes: readonly string[]; accent: string; accentRgb: string }>;

function reducedMotionRequested(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function ProfessionalJourneyShowcase({ content }: { content: ProfessionalJourneyContent }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [direction, setDirection] = useState<Direction | null>(null);
  const [autoplay, setAutoplay] = useState(true);
  const [isVisible, setIsVisible] = useState(false);
  const containerRef = useRef<HTMLElement | null>(null);
  const reducedMotionRef = useRef(false);
  const catalogue = listPublicProfessionals();
  const agriculturalStory = content.stories.find(({ id }) => id === 'agricultural-advisor');
  const marketingStory = content.stories.find(({ id }) => id === 'digital-marketing-professional');
  const scenes: readonly SpotlightScene[] = SCENE_ORDER.map((id) => {
    const professional = catalogue.find(({ slug }) => slug === id);
    const story = id === 'agricultural-advisory' ? agriculturalStory : id === 'digital-marketing' ? marketingStory : undefined;
    const palette = { 'agricultural-advisory': ['#2a8c56', '42 140 86'], 'digital-marketing': ['#1769d2', '23 105 210'], 'private-tutoring': ['#b77908', '183 121 8'], 'trading-advisory': ['#087d84', '8 125 132'] }[id];
    return { id, name: story?.selectorLabel ?? professional?.name ?? id, context: story?.contextLabel ?? professional?.domain ?? '', capability: story?.stages[5].summary ?? professional?.summary ?? '', outcomes: professional?.outcomes.slice(0, 3) ?? [], accent: palette[0], accentRgb: palette[1] };
  });

  useEffect(() => {
    reducedMotionRef.current = reducedMotionRequested();
    if (reducedMotionRef.current) setAutoplay(false);
    const node = containerRef.current;
    if (!node || typeof IntersectionObserver === 'undefined') { setIsVisible(true); return; }
    const observer = new IntersectionObserver((entries) => setIsVisible(entries.some((entry) => entry.isIntersecting)), { threshold: 0.3 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!autoplay || !isVisible || direction !== null || document.visibilityState === 'hidden') return;
    const timer = window.setTimeout(() => setDirection(1), AUTO_ADVANCE_MS);
    return () => window.clearTimeout(timer);
  }, [activeIndex, autoplay, direction, isVisible]);

  function move(nextDirection: Direction) {
    if (direction !== null) return;
    setAutoplay(false);
    if (reducedMotionRef.current) { setActiveIndex((index) => (index + nextDirection + scenes.length) % scenes.length); return; }
    setDirection(nextDirection);
  }

  function settleTransport(propertyName: string) {
    if (propertyName !== 'transform' || direction === null) return;
    setActiveIndex((index) => (index + direction + scenes.length) % scenes.length);
    setDirection(null);
  }

  function replay() {
    setDirection(null);
    setActiveIndex(0);
    setAutoplay(!reducedMotionRef.current);
  }

  const positions = [-2, -1, 0, 1, 2] as const;
  const announcedPosition = direction ?? 0;
  const activeScene = scenes[(activeIndex + announcedPosition + scenes.length) % scenes.length];
  return (
    <section ref={containerRef} className="journey-showcase agent-spotlight" data-professional={activeScene.id} data-transport={direction === null ? 'settled' : direction > 0 ? 'forward' : 'backward'} aria-labelledby="journey-showcase-title" style={{ '--spotlight-accent': activeScene.accent, '--spotlight-accent-rgb': activeScene.accentRgb } as React.CSSProperties}>
      <h2 id="journey-showcase-title" className="visually-hidden">WAOOAW professional spotlight</h2>
      <p className="visually-hidden" aria-live="polite">Showing {activeScene.name}</p>
      <div className="spotlight-stage">
        <button className="spotlight-control spotlight-control-previous" type="button" aria-label="Previous professional" disabled={direction !== null} onClick={() => move(-1)}><ChevronLeft aria-hidden="true" size={22} /></button>
        <button className="spotlight-control spotlight-control-next" type="button" aria-label="Next professional" disabled={direction !== null} onClick={() => move(1)}><ChevronRight aria-hidden="true" size={22} /></button>
        <button className="spotlight-control spotlight-replay" type="button" aria-label="Replay professional sequence" disabled={direction !== null} onClick={replay}><RotateCcw aria-hidden="true" size={18} /></button>
        <div className={`spotlight-film-track${direction === 1 ? ' is-moving-forward' : direction === -1 ? ' is-moving-backward' : ''}`} data-testid="spotlight-film-track" onTransitionEnd={(event) => settleTransport(event.propertyName)}>
          {positions.map((position) => { const scene = scenes[(activeIndex + position + scenes.length) % scenes.length]; return <FilmFrame key={position} scene={scene} position={position} isCurrent={position === announcedPosition} />; })}
        </div>
      </div>
    </section>
  );
}

function FilmFrame({ scene, position, isCurrent }: { scene: SpotlightScene; position: number; isCurrent: boolean }) {
  const Icon = scene.id === 'agricultural-advisory' ? Sprout : scene.id === 'digital-marketing' ? Megaphone : scene.id === 'private-tutoring' ? BookOpen : ChartCandlestick;
  const frameCode = Math.abs(position) % 2 === 0 ? '12' : '11A';
  return (
    <article className={`spotlight-film-cell${isCurrent ? ' is-current' : ''}`} data-position={position} data-scene={scene.id} aria-hidden={!isCurrent}>
      <span className="spotlight-film-code spotlight-film-code-top" aria-hidden="true">{frameCode}</span><span className="spotlight-film-code spotlight-film-code-bottom" aria-hidden="true">{frameCode}</span>
      <div className="spotlight-frame" style={{ '--frame-accent': scene.accent, '--frame-accent-rgb': scene.accentRgb } as React.CSSProperties}>
        <SceneArtwork sceneId={scene.id} />
        <header className="spotlight-identity"><span className="spotlight-identity-icon"><Icon aria-hidden="true" size={24} /></span><span><strong>{scene.name}</strong><small>{scene.context}</small></span></header>
        <p className="spotlight-capability">{scene.capability}</p>
        <div className="spotlight-signals">{scene.outcomes.map((outcome, index) => <span className="spotlight-signal" key={outcome}><small>{index === 0 ? 'Focus' : index === 1 ? 'Active work' : 'Outcome'}</small><strong>{outcome}</strong><em>{index === 2 ? 'Review' : 'Ready'}</em></span>)}</div>
      </div>
    </article>
  );
}

function SceneArtwork({ sceneId }: { sceneId: SceneId }) {
  return <div className={`spotlight-artwork artwork-${sceneId}`} aria-hidden="true">
    {sceneId === 'digital-marketing' ? <><span className="artwork-post" /><span className="artwork-post" /><span className="artwork-chart"><i /><i /><i /><i /></span></> : null}
    {sceneId === 'private-tutoring' ? <><span className="artwork-book"><i /><i /></span><span className="artwork-grade">A+</span><span className="artwork-rule" /></> : null}
    {sceneId === 'agricultural-advisory' ? <><span className="artwork-sun" /><span className="artwork-field"><i /><i /><i /><i /></span><span className="artwork-leaf"><i /><i /></span></> : null}
    {sceneId === 'trading-advisory' ? <><span className="artwork-grid" /><span className="artwork-candles"><i /><i /><i /><i /><i /></span><span className="artwork-trend" /></> : null}
  </div>;
}
