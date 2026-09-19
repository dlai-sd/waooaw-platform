// Implements: work-contracts/WC-093-public-auth-experience-finalization.md WC093-A02, WC093-A03, WC093-A08
// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §24
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability), C-063 (Data Minimisation)
'use client';

import { BookOpen, ChartCandlestick, ChevronLeft, ChevronRight, Megaphone, RotateCcw, Sprout } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { listPublicProfessionals } from '@/config/professionals';
import type { ProfessionalJourneyContent } from '@/lib/professional-journey-content';

const AUTO_ADVANCE_MS = 3000;
const SCENE_ORDER = ['agricultural-advisory', 'digital-marketing', 'private-tutoring', 'trading-advisory'] as const;
const SLOT_STYLE = [
  { scale: 1, opacity: 1, blur: 0, zIndex: 40 },
  { scale: 0.8, opacity: 0.55, blur: 1.5, zIndex: 30 },
  { scale: 0.68, opacity: 0.42, blur: 2, zIndex: 20 },
  { scale: 0.8, opacity: 0.55, blur: 1.5, zIndex: 30 },
] as const;
type SceneId = (typeof SCENE_ORDER)[number];
type SpotlightScene = Readonly<{
  id: SceneId;
  name: string;
  context: string;
  capability: string;
  outcomes: readonly string[];
}>;

export function ProfessionalJourneyShowcase({ content }: { content: ProfessionalJourneyContent }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [stageWidth, setStageWidth] = useState(720);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const catalogue = listPublicProfessionals();
  const agriculturalStory = content.stories.find(({ id }) => id === 'agricultural-advisor');
  const marketingStory = content.stories.find(({ id }) => id === 'digital-marketing-professional');
  const scenes: readonly SpotlightScene[] = SCENE_ORDER.map((id) => {
    const professional = catalogue.find(({ slug }) => slug === id);
    const story =
      id === 'agricultural-advisory' ? agriculturalStory : id === 'digital-marketing' ? marketingStory : undefined;
    return {
      id,
      name: story?.selectorLabel ?? professional?.name ?? id,
      context: story?.contextLabel ?? professional?.domain ?? '',
      capability: story?.stages[5].summary ?? professional?.summary ?? '',
      outcomes: professional?.outcomes.slice(0, 3) ?? [],
    };
  });

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const updateWidth = () => setStageWidth(stage.clientWidth || 720);
    updateWidth();
    if (typeof ResizeObserver === 'undefined') return;
    const observer = new ResizeObserver(updateWidth);
    observer.observe(stage);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const timer = window.setInterval(
      () => setActiveIndex((index) => (index - 1 + scenes.length) % scenes.length),
      AUTO_ADVANCE_MS
    );
    return () => window.clearInterval(timer);
  }, [activeIndex, scenes.length]);

  const cardWidth = stageWidth * 0.78;
  const radiusX = cardWidth * 0.55;
  const radiusY = cardWidth * 0.14;

  function selectScene(index: number) {
    setActiveIndex((index + scenes.length) % scenes.length);
  }

  return (
    <section className="orbit-showcase" aria-labelledby="journey-showcase-title">
      <h2 id="journey-showcase-title" className="visually-hidden">
        WAOOAW professional spotlight
      </h2>
      <p className="visually-hidden" aria-live="polite">
        Showing {scenes[activeIndex].name}
      </p>
      <div className="orbit-stage" ref={stageRef}>
        <div className="orbit-core" aria-hidden="true" />
        <div className="orbit-ring" aria-hidden="true" />
        <div className="professional-orbit">
          {scenes.map((scene, index) => {
            const slot = (index - activeIndex + scenes.length) % scenes.length;
            const style = SLOT_STYLE[slot];
            const angle = (slot / scenes.length) * Math.PI * 2 - Math.PI / 2;
            const offsetX = Math.cos(angle) * radiusX;
            const offsetY = Math.sin(angle) * radiusY;
            return (
              <OrbitCard
                key={scene.id}
                scene={scene}
                front={slot === 0}
                onSelect={() => selectScene(index)}
                style={{
                  opacity: style.opacity,
                  filter: style.blur ? `blur(${style.blur}px) saturate(.85)` : 'none',
                  zIndex: style.zIndex,
                  transform: `translate(-50%, -50%) translate(${offsetX}px, ${offsetY}px) scale(${style.scale})`,
                }}
              />
            );
          })}
        </div>
        <button
          className="orbit-nav orbit-nav-previous"
          type="button"
          aria-label="Previous professional"
          onClick={() => selectScene(activeIndex - 1)}
        >
          <ChevronLeft aria-hidden="true" size={18} />
        </button>
        <button
          className="orbit-nav orbit-nav-next"
          type="button"
          aria-label="Next professional"
          onClick={() => selectScene(activeIndex + 1)}
        >
          <ChevronRight aria-hidden="true" size={18} />
        </button>
      </div>
      <div className="orbit-footer">
        <span>
          {String(activeIndex + 1).padStart(2, '0')} / {String(scenes.length).padStart(2, '0')}
        </span>
        <span className="orbit-dots">
          {scenes.map((scene, index) => (
            <button
              aria-label={`Show ${scene.name}`}
              aria-pressed={index === activeIndex}
              className={index === activeIndex ? 'active' : ''}
              key={scene.id}
              onClick={() => selectScene(index)}
              type="button"
            />
          ))}
        </span>
      </div>
    </section>
  );
}

function OrbitCard({
  front,
  onSelect,
  scene,
  style,
}: { front: boolean; onSelect: () => void; scene: SpotlightScene; style: React.CSSProperties }) {
  const Icon =
    scene.id === 'agricultural-advisory'
      ? Sprout
      : scene.id === 'digital-marketing'
        ? Megaphone
        : scene.id === 'private-tutoring'
          ? BookOpen
          : ChartCandlestick;
  return (
    <article className={`orbit-card ${front ? 'front' : 'back'}`} style={style}>
      <div className="orbit-card-head">
        <div className="orbit-card-heading">
          <span className="orbit-card-icon">
            <Icon aria-hidden="true" size={22} />
          </span>
          <span>
            <strong>{scene.name}</strong>
            <small>{scene.context}</small>
          </span>
        </div>
        <button aria-label={`Bring ${scene.name} to front`} className="orbit-refresh" type="button" onClick={onSelect}>
          <RotateCcw aria-hidden="true" size={15} />
        </button>
      </div>
      <p className="orbit-capability">{scene.capability}</p>
      <div className="orbit-workflow">
        {scene.outcomes.map((outcome, index) => (
          <div
            className="orbit-work-card"
            data-role={index === 1 ? 'active' : index === 2 ? 'outcome' : 'focus'}
            key={outcome}
          >
            <div className="orbit-work-label">{index === 0 ? 'Focus' : index === 1 ? 'Active work' : 'Outcome'}</div>
            <div className="orbit-work-title">{outcome}</div>
            <div className={index === 2 ? 'orbit-status review' : 'orbit-status ready'}>
              <span />
              {index === 2 ? 'Review' : 'Ready'}
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
