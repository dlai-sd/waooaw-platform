// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §7, §9, §10.4
// Constitutional basis: C-002 (Evidence Integrity), C-059 (Implementation Traceability), C-063 (Data Minimisation)
'use client';

import { AlertCircle, Building2, Check, CheckCircle2, Circle, CircleDot, Radar, Sprout, Target } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import type { JourneyRailId, JourneyStageId, ProfessionalJourneyContent, ProfessionalStoryId } from '@/lib/professional-journey-content';

const RAIL_ORDER: readonly JourneyRailId[] = ['business', 'goals', 'ways-of-working', 'working'];
const RAIL_ICONS: Readonly<Record<JourneyRailId, typeof Building2>> = { business: Building2, goals: Target, 'ways-of-working': Check, working: Radar };
const STORY_ORDER: readonly ProfessionalStoryId[] = ['agricultural-advisor', 'digital-marketing-professional'];
const STAGE_DURATION_MS = 800;
const TOTAL_AUTO_STAGES = 12; // two 6-stage stories walked once; 12 * 800ms = 9.6s total

type Phase = 'pending' | 'auto' | 'manual' | 'settled';
type StageState = 'intro' | 'active' | 'attention' | 'complete';

const STAGE_ICONS: Readonly<Record<StageState, typeof Circle>> = { intro: Circle, active: CircleDot, attention: AlertCircle, complete: CheckCircle2 };

function reducedMotionRequested(): boolean {
  return typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
}

export function ProfessionalJourneyShowcase({ content }: { content: ProfessionalJourneyContent }) {
  const [phase, setPhase] = useState<Phase>('pending');
  const [storyId, setStoryId] = useState<ProfessionalStoryId>('agricultural-advisor');
  const [stageId, setStageId] = useState<JourneyStageId>('opening');
  const containerRef = useRef<HTMLElement | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const autoIndexRef = useRef(0);
  const hasInteractedRef = useRef(false);
  const hasStartedRef = useRef(false);

  const storyById = useMemo(() => Object.fromEntries(content.stories.map((story) => [story.id, story])) as Record<ProfessionalStoryId, ProfessionalJourneyContent['stories'][number]>, [content]);

  function clearTimer() {
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }

  function applyAutoIndex(index: number) {
    const storyIndex = Math.floor(index / 6);
    const stageIndex = index % 6;
    setStoryId(STORY_ORDER[storyIndex]);
    setStageId(storyById[STORY_ORDER[storyIndex]].stages[stageIndex].id);
  }

  function scheduleNext() {
    clearTimer();
    timerRef.current = setTimeout(() => {
      if (document.visibilityState === 'hidden') {
        scheduleNext();
        return;
      }
      const nextIndex = autoIndexRef.current + 1;
      if (nextIndex >= TOTAL_AUTO_STAGES) {
        setPhase('settled');
        return;
      }
      autoIndexRef.current = nextIndex;
      applyAutoIndex(nextIndex);
      scheduleNext();
    }, STAGE_DURATION_MS);
  }

  function startAutoplay() {
    if (hasInteractedRef.current || hasStartedRef.current) return;
    hasStartedRef.current = true;
    autoIndexRef.current = 0;
    applyAutoIndex(0);
    setPhase('auto');
    scheduleNext();
  }

  function cancelToManual(nextStory: ProfessionalStoryId, nextStage: JourneyStageId) {
    hasInteractedRef.current = true;
    hasStartedRef.current = true;
    clearTimer();
    setStoryId(nextStory);
    setStageId(nextStage);
    setPhase('manual');
  }

  useEffect(() => {
    if (reducedMotionRequested()) {
      hasInteractedRef.current = true;
      hasStartedRef.current = true;
      setStoryId('agricultural-advisor');
      setStageId('working');
      setPhase('settled');
      return;
    }
    const node = containerRef.current;
    if (!node || typeof IntersectionObserver === 'undefined') {
      return;
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        startAutoplay();
      }
    }, { threshold: 0.3 });
    observer.observe(node);
    return () => observer.disconnect();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    function onVisibilityChange() {
      if (document.visibilityState === 'visible' && phase === 'auto' && timerRef.current === null) {
        scheduleNext();
      }
    }
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  useEffect(() => () => clearTimer(), []);

  const activeStory = storyById[storyId];
  const activeStageIndex = activeStory.stages.findIndex((stage) => stage.id === stageId);
  const activeStage = activeStory.stages[Math.max(activeStageIndex, 0)];
  const activeRailId = activeStage.railId;
  const isSettled = phase === 'settled';

  function stageStateFor(index: number): StageState {
    if (isSettled) return index === activeStageIndex ? 'complete' : 'intro';
    if (index < activeStageIndex) return 'complete';
    if (index === activeStageIndex) return 'active';
    if (index === activeStageIndex + 1 && activeStory.stages[index].id === 'ready') return 'attention';
    return 'intro';
  }

  const visibleState = stageStateFor(activeStageIndex);
  const StageIcon = STAGE_ICONS[visibleState];

  function selectStory(nextStory: ProfessionalStoryId) {
    const nearestStage = activeStory.stages.find((stage) => stage.id === stageId) ? stageId : 'opening';
    cancelToManual(nextStory, nearestStage);
  }

  function selectRail(railId: JourneyRailId) {
    const firstStage = activeStory.stages.find((stage) => stage.railId === railId);
    if (firstStage) cancelToManual(storyId, firstStage.id);
  }

  return (
    <section ref={containerRef} className="journey-showcase" data-story-id={storyId} data-stage-id={activeStage.id} aria-labelledby="journey-showcase-title" aria-describedby="journey-showcase-summary">
      <h2 id="journey-showcase-title" className="visually-hidden">Two example WAOOAW professional journeys</h2>
      <p id="journey-showcase-summary" className="visually-hidden">{content.accessibleSummary}</p>
      <div className="journey-selector" role="group" aria-label="Choose a professional story">
        {content.stories.map((story) => {
          const Icon = story.id === 'agricultural-advisor' ? Sprout : Building2;
          return (
            <button key={story.id} type="button" className="journey-selector-option" aria-pressed={storyId === story.id} onClick={() => selectStory(story.id)}>
              <Icon aria-hidden="true" size={18} />
              <span><strong>{story.selectorLabel}</strong><small>{story.contextLabel}</small></span>
            </button>
          );
        })}
      </div>
      <div className="journey-viewport">
        <div className="journey-illustration" aria-hidden="true">
          {storyId === 'agricultural-advisor' ? <Sprout size={40} /> : <Building2 size={40} />}
          <span className="visually-hidden">{activeStory.illustrationLabel}</span>
        </div>
        <article className="journey-card" data-state={visibleState} key={`${storyId}:${activeStage.id}`}>
          <StageIcon aria-hidden="true" size={20} />
          <h3>{activeStage.title}</h3>
          <p>{activeStage.summary}</p>
          <ul>{activeStage.details.map((detail) => <li key={detail}>{detail}</li>)}</ul>
        </article>
      </div>
      <nav className="professional-journey-rail" aria-label="Journey stages">
        {RAIL_ORDER.map((railId) => {
          const RailIcon = RAIL_ICONS[railId];
          return (
            <button key={railId} type="button" aria-pressed={activeRailId === railId} onClick={() => selectRail(railId)}>
              <RailIcon aria-hidden="true" size={16} />
              <span>{content.railLabels[railId]}</span>
            </button>
          );
        })}
      </nav>
      {isSettled ? <p className="journey-settled">{content.finalMessage}</p> : null}
    </section>
  );
}
