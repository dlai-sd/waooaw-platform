// Implements: work-contracts/WC-093-public-auth-experience-finalization.md WC093-A02, WC093-A03, WC093-A08
// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R009, WC105-R010, WC105-R011
// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §24
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability), C-063 (Data Minimisation)
'use client';

import {
  BookOpen,
  ChartCandlestick,
  ChevronLeft,
  ChevronRight,
  CircleDollarSign,
  Clock3,
  Globe2,
  Megaphone,
  RotateCcw,
  Search,
  Smartphone,
  Sprout,
  TrendingDown,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import type { ProfessionalJourneyContent } from '@/lib/professional-journey-content';

const AUTO_ADVANCE_MS = 10000;
const CHAOS_ADVANCE_MS = 3500;
const SCENE_ORDER = ['digital-marketing', 'agricultural-advisory', 'private-tutoring', 'trading-advisory'] as const;
const SLOT_STYLE = [
  { scale: 1, opacity: 1, blur: 0, zIndex: 40 },
  { scale: 0.8, opacity: 0.352, blur: 1.5, zIndex: 30 },
  { scale: 0.68, opacity: 0.2688, blur: 2, zIndex: 20 },
  { scale: 0.8, opacity: 0.352, blur: 1.5, zIndex: 30 },
] as const;
type SceneId = (typeof SCENE_ORDER)[number];
type SpotlightScene = Readonly<{
  id: SceneId;
  name: string;
  context: string;
  capability: readonly [string, string, string];
  outcomes: readonly string[];
}>;

const SCENES: readonly SpotlightScene[] = [
  {
    id: 'digital-marketing',
    name: 'Digital Marketing Agent',
    context: 'Growing business',
    capability: ['Watch ', 'chaos turn into clarity', ' - You only step in when it matters.'],
    outcomes: ['Planning', 'Execution', 'Optimization'],
  },
  {
    id: 'agricultural-advisory',
    name: 'Agriculture AI Expert',
    context: 'Farm business',
    capability: ['Your professional ', 'monitors the field', ' and surfaces decisions only when the season demands.'],
    outcomes: ['Season planning', 'Crop guidance', 'Risk-aware recommendations'],
  },
  {
    id: 'private-tutoring',
    name: 'Private Tutor',
    context: 'Learning & education',
    capability: ['Your tutor ', 'adapts to the learner', ' and brings you in only at the moments that matter.'],
    outcomes: ['Learning plan', 'Lesson adaptation', 'Progress assessment'],
  },
  {
    id: 'trading-advisory',
    name: 'Share Market Trading Expert',
    context: 'Markets & investing',
    capability: ['Your expert ', 'watches the markets', ' and asks you only when an opportunity or risk appears.'],
    outcomes: ['Portfolio strategy', 'Signal monitoring', 'Risk-adjusted actions'],
  },
];

const CHAOS_ITEMS = [
  { Icon: Search, label: 'SEO', detail: 'Rankings dropping, no one owns it', x: '18%', y: '22%', rotate: '-12deg' },
  {
    Icon: Smartphone,
    label: 'Social content',
    detail: 'One idea across five platforms',
    x: '78%',
    y: '20%',
    rotate: '9deg',
  },
  { Icon: CircleDollarSign, label: 'Ad budget', detail: 'Spend up, returns flat', x: '15%', y: '50%', rotate: '-7deg' },
  { Icon: Globe2, label: 'Website', detail: 'Updates queued, links broken', x: '82%', y: '52%', rotate: '12deg' },
  { Icon: Clock3, label: 'Hours lost', detail: '20+ hours each week on ops', x: '20%', y: '80%', rotate: '10deg' },
  { Icon: TrendingDown, label: 'Outcomes', detail: 'Growth and ROI unclear', x: '76%', y: '82%', rotate: '-14deg' },
] as const;

const ORDER_ITEMS = [
  { label: 'Planning', metric: '+38% reach' },
  { label: 'Execution', metric: '-24% cost' },
  { label: 'Optimization', metric: '2.4x ROAS' },
] as const;

export function ProfessionalJourneyShowcase({ content: _content }: { content: ProfessionalJourneyContent }) {
  const [activeIndex, setActiveIndex] = useState(0);
  const [chaosIndex, setChaosIndex] = useState(0);
  const [stageWidth, setStageWidth] = useState(720);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const scenes = SCENES;

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

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const timer = window.setInterval(
      () => setChaosIndex((index) => (index + 1) % CHAOS_ITEMS.length),
      CHAOS_ADVANCE_MS
    );
    return () => window.clearInterval(timer);
  }, []);

  const originalCardWidth = stageWidth * 0.936;
  const radiusX = originalCardWidth * 0.55;
  const radiusY = stageWidth < 400 ? 0 : originalCardWidth * 0.14;

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
                chaosIndex={chaosIndex}
                onSelect={() => selectScene(index)}
                style={{
                  opacity: style.opacity,
                  filter: style.blur ? `blur(${style.blur}px) saturate(.85)` : 'none',
                  zIndex: style.zIndex,
                  transform: `translate(-50%, -50%) translate(${offsetX}px, ${offsetY}px) scaleX(${style.scale})`,
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
  chaosIndex,
  front,
  onSelect,
  scene,
  style,
}: { chaosIndex: number; front: boolean; onSelect: () => void; scene: SpotlightScene; style: React.CSSProperties }) {
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
      <p className="orbit-capability">
        {scene.capability[0]}
        <strong>{scene.capability[1]}</strong>
        {scene.capability[2]}
      </p>
      {scene.id === 'digital-marketing' ? (
        <ChaosToOrder chaosIndex={chaosIndex} />
      ) : (
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
      )}
    </article>
  );
}

function ChaosToOrder({ chaosIndex }: { chaosIndex: number }) {
  return (
    <div className="chaos-order">
      <div className="chaos-pane">
        <div className="chaos-heading">Digital Marketing on fire</div>
        <div className="chaos-swarm">
          {CHAOS_ITEMS.map(({ Icon, detail, label, rotate, x, y }, index) => (
            <div
              className={`chaos-item ${index === chaosIndex ? 'active' : ''}`}
              key={label}
              style={
                {
                  '--chaos-delay': `${index * -0.38}s`,
                  '--chaos-x': x,
                  '--chaos-y': y,
                  '--chaos-rotate': rotate,
                } as React.CSSProperties
              }
            >
              <span>
                <Icon aria-hidden="true" size={12} />
                {label}
              </span>
              <small>{detail}</small>
            </div>
          ))}
        </div>
      </div>
      <div className="chaos-core" aria-hidden="true">
        <span>AI</span>
      </div>
      <div className="order-pane">
        <div className="chaos-heading">With WAOOAW - order & results</div>
        <div className="order-list">
          {ORDER_ITEMS.map((item) => (
            <div className="order-row" key={item.label}>
              <span className="order-dot" />
              <strong>{item.label}</strong>
              <small>{item.metric}</small>
              <span className="order-status">Ready</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
