'use client';

// Implements: architecture/reference/ux/wc-078-visual-experience-implementation-plan.md §10.2 (WC-02)
// Constitutional basis: C-059 (Implementation Traceability)

import { useEffect } from 'react';

const scrollThreshold = 24;

export function HeaderScrollState() {
  useEffect(() => {
    function update() {
      document.documentElement.dataset.headerScrolled = window.scrollY > scrollThreshold ? 'true' : 'false';
    }
    update();
    window.addEventListener('scroll', update, { passive: true });
    return () => window.removeEventListener('scroll', update);
  }, []);
  return null;
}
