/** Centralized animation utilities using @mkbabb/keyframes.js */

import { CSSKeyframesAnimation } from '@mkbabb/keyframes.js';

/** Timing presets */
export const DURATION = {
  press: 100,
  release: 200,
  slide: 250,
  bounce: 600,
} as const;

const animConfigs = {
  instant: { duration: 150 },
  fast: { duration: DURATION.release },
  normal: { duration: 350 },
  smooth: { duration: DURATION.slide },
} as const;

type AnimTiming = keyof typeof animConfigs;

/** Stagger configurations for cascading animations */
export const staggerConfig = {
  tight: 50,
  normal: 100,
  loose: 150,
  veryLoose: 200,
} as const;

/** Animation state presets */
export const animationStates = {
  hidden: { opacity: '0', transform: 'translateY(-8px) scale(0.98)' },
  visible: { opacity: '1', transform: 'translateY(0) scale(1)' },
  exit: { opacity: '0', transform: 'translateY(-4px) scale(0.98)' },
} as const;

/** Animate element visibility with slide+fade */
export function animateVisibility(
  element: HTMLElement,
  show: boolean,
  options: {
    timing?: AnimTiming;
    onComplete?: () => void;
  } = {}
): CSSKeyframesAnimation<any> | undefined {
  const { timing = 'fast', onComplete } = options;
  const config = animConfigs[timing];

  const anim = new CSSKeyframesAnimation<any>({ duration: config.duration, fillMode: 'forwards' }, element);

  if (show) {
    element.style.display = 'block';
    anim.fromVars([
      { opacity: '0', transform: 'translateY(-4px) scale(0.98)' },
      { opacity: '1', transform: 'translateY(0) scale(1)' },
    ]);
  } else {
    anim.fromVars([
      { opacity: '1', transform: 'translateY(0) scale(1)' },
      { opacity: '0', transform: 'translateY(-4px) scale(0.98)' },
    ]);
  }

  anim.play().then(() => {
    if (!show) element.style.display = 'none';
    onComplete?.();
  });

  return anim;
}

/** Animate container height to fit visible children */
export function animateContainerHeight(
  container: HTMLElement,
  timing: AnimTiming = 'normal'
): CSSKeyframesAnimation<any> {
  const config = animConfigs[timing];
  const children = Array.from(container.children) as HTMLElement[];

  let totalHeight = 0;
  children.forEach(child => {
    if (child.style.display !== 'none' && child.style.opacity !== '0') {
      totalHeight += child.offsetHeight + parseInt(getComputedStyle(child).marginBottom || '0');
    }
  });

  const anim = new CSSKeyframesAnimation<any>({ duration: config.duration, fillMode: 'forwards' }, container);
  anim.fromVars([
    { height: `${container.offsetHeight}px` },
    { height: `${totalHeight}px` },
  ]);
  anim.play();
  return anim;
}

/** Simple fade-in animation */
export function fadeTransition(
  element: HTMLElement,
  timing: AnimTiming = 'fast'
): CSSKeyframesAnimation<any> {
  const config = animConfigs[timing];
  const anim = new CSSKeyframesAnimation<any>({ duration: config.duration, fillMode: 'forwards' }, element);
  anim.fromVars([{ opacity: '0' }, { opacity: '1' }]);
  anim.play();
  return anim;
}

/** Auto-hide element after delay with fade-out */
export function createAutoHide(
  element: HTMLElement,
  delay: number = 10000,
  onHide?: () => void
) {
  let timer: ReturnType<typeof setTimeout> | null = null;

  const start = () => {
    cancel();
    timer = setTimeout(() => {
      animateVisibility(element, false, { onComplete: onHide });
    }, delay);
  };

  const cancel = () => {
    if (timer) {
      clearTimeout(timer);
      timer = null;
    }
  };

  return { start, cancel };
}

// Dynamic rainbow gradient generator
export function generateRainbowGradient(steps: number = 7): string {
  const colors = [
    'rgb(239, 68, 68)',   // red-500
    'rgb(249, 115, 22)',  // orange-500
    'rgb(234, 179, 8)',   // yellow-500
    'rgb(34, 197, 94)',   // green-500
    'rgb(6, 182, 212)',   // cyan-500
    'rgb(59, 130, 246)',  // blue-500
    'rgb(147, 51, 234)',  // purple-500
    'rgb(236, 72, 153)',  // pink-500
  ];

  const selectedColors = [];
  for (let i = 0; i < steps; i++) {
    const index = Math.floor((i / (steps - 1)) * (colors.length - 1));
    selectedColors.push(colors[index]);
  }

  return `linear-gradient(90deg, ${selectedColors.join(', ')})`;
}

/**
 * Temperature gradient: cold blue -> neutral -> warm amber -> hot red.
 * Used for frequency visualization on definitions and edit sliders.
 */
export const TEMPERATURE_GRADIENT = 'linear-gradient(90deg, rgb(59, 130, 246), rgb(6, 182, 212), rgb(34, 197, 94), rgb(234, 179, 8), rgb(249, 115, 22), rgb(239, 68, 68))';

/**
 * Get temperature color for a 0.0-1.0 score.
 * Returns an HSL string mapping cold->hot.
 */
export function temperatureColor(score: number): string {
  const clamped = Math.max(0, Math.min(1, score));
  // 220 (cold blue) -> 40 (warm amber) -> 0 (hot red)
  const hue = clamped < 0.5
    ? 220 - (clamped * 2) * 180
    : 40 - ((clamped - 0.5) * 2) * 40;
  const saturation = 60 + clamped * 30;
  const lightness = Math.max(40, 70 - clamped * 40);
  return `hsl(${hue}, ${saturation}%, ${lightness}%)`;
}

// Animated rainbow gradient with time-based shifting
export function generateAnimatedRainbowGradient(): string {
  const baseColors = [
    'rgb(239, 68, 68)',   // red-500
    'rgb(249, 115, 22)',  // orange-500
    'rgb(234, 179, 8)',   // yellow-500
    'rgb(34, 197, 94)',   // green-500
    'rgb(6, 182, 212)',   // cyan-500
    'rgb(59, 130, 246)',  // blue-500
    'rgb(147, 51, 234)',  // purple-500
    'rgb(236, 72, 153)',  // pink-500
  ];

  const extendedColors = [...baseColors, ...baseColors.slice(0, 3)];

  return `linear-gradient(90deg, ${extendedColors.join(', ')})`;
}

// Re-export stagger tokens from the directory's constants module
export { STAGGER_FAST, STAGGER, STAGGER_SLOW } from './animations/constants';
