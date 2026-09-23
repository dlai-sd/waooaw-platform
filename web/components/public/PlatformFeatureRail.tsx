'use client';

// Implements: work-contracts/WC-105-auth-ui-runtime-defect-repair.md WC105-R024
// Constitutional basis: C-042 (Vocabulary Mandate), C-049 (Honest Limitation), C-059 (Implementation Traceability)

import { BriefcaseBusiness, ChevronLeft, ChevronRight, Languages, MessageCircleMore } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

const features = [
  {
    title: 'Work with your WAOOAW professional on WhatsApp',
    description:
      'Use a familiar channel for written and voice conversations while governed records remain connected to the professional relationship.',
    icon: MessageCircleMore,
  },
  {
    title: 'Built for real business growth',
    description:
      'Every WAOOAW professional supports a clear journey from hiring and induction through ongoing grooming and earning business outcomes, within declared authority.',
    icon: BriefcaseBusiness,
  },
  {
    title: 'Your language, written or spoken',
    description:
      "WAOOAW professionals communicate in the customer's selected supported language through text and voice without overstating unsupported languages or channels.",
    icon: Languages,
  },
] as const;

export function PlatformFeatureRail() {
  const [activeIndex, setActiveIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const interactionPaused = useRef(false);
  const touchStartX = useRef<number | null>(null);

  useEffect(() => {
    if (paused || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const timer = window.setInterval(() => setActiveIndex((current) => (current + 1) % features.length), 7000);
    return () => window.clearInterval(timer);
  }, [paused]);

  function select(index: number) {
    interactionPaused.current = true;
    setPaused(true);
    setActiveIndex((index + features.length) % features.length);
  }

  function pauseForInteraction() {
    interactionPaused.current = true;
    setPaused(true);
  }

  return (
    <section
      aria-label="Platform features"
      className="platform-feature-rail"
      onFocusCapture={pauseForInteraction}
      onKeyDown={(event) => {
        if (event.key === 'ArrowLeft') select(activeIndex - 1);
        if (event.key === 'ArrowRight') select(activeIndex + 1);
      }}
      onPointerEnter={() => setPaused(true)}
      onPointerLeave={() => {
        if (!interactionPaused.current) setPaused(false);
      }}
      onTouchEnd={(event) => {
        const startX = touchStartX.current;
        touchStartX.current = null;
        if (startX === null) return;
        const distance = event.changedTouches[0].clientX - startX;
        if (Math.abs(distance) < 40) return;
        select(activeIndex + (distance < 0 ? 1 : -1));
      }}
      onTouchStart={(event) => {
        pauseForInteraction();
        touchStartX.current = event.touches[0].clientX;
      }}
    >
      <div className="platform-feature-viewport">
        <div className="platform-feature-track" style={{ transform: `translateX(-${activeIndex * 100}%)` }}>
          {features.map((feature, index) => {
            const Icon = feature.icon;
            return (
              <article aria-hidden={index !== activeIndex} className="platform-feature-card" key={feature.title}>
                <Icon aria-hidden="true" size={34} />
                <div>
                  <h3>{feature.title}</h3>
                  <p>{feature.description}</p>
                </div>
              </article>
            );
          })}
        </div>
      </div>
      <div className="platform-feature-controls">
        <button aria-label="Previous platform feature" onClick={() => select(activeIndex - 1)} type="button">
          <ChevronLeft aria-hidden="true" size={22} />
        </button>
        <span aria-live="polite">
          {String(activeIndex + 1).padStart(2, '0')} / {String(features.length).padStart(2, '0')}
        </span>
        <button aria-label="Next platform feature" onClick={() => select(activeIndex + 1)} type="button">
          <ChevronRight aria-hidden="true" size={22} />
        </button>
      </div>
    </section>
  );
}
