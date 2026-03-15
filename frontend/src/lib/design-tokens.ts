/** Centralized animation timing constants for GSAP usage */
export const GSAP_EASE = {
  spring: 'back.out(1.2)',
  press: 'power2.out',
  smooth: 'power2.inOut',
} as const;

export const GSAP_DURATION = {
  press: 0.1,
  release: 0.2,
  slide: 0.25,
  bounce: 0.6,
} as const;
