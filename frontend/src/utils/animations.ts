import { gsap } from 'gsap';
import { CSSPlugin } from 'gsap/CSSPlugin';
import { GSAP_EASE, GSAP_DURATION } from '@/lib/design-tokens';

// Register GSAP plugins to prevent property warnings
gsap.registerPlugin(CSSPlugin);

// Re-export design tokens as the single source of truth for GSAP timings
export { GSAP_EASE, GSAP_DURATION };

// Standard animation configs derived from design tokens
const animConfigs = {
  instant: { duration: 0.15, ease: GSAP_EASE.press },
  fast: { duration: GSAP_DURATION.release, ease: GSAP_EASE.press },
  normal: { duration: 0.35, ease: GSAP_EASE.press },
  smooth: { duration: GSAP_DURATION.slide, ease: GSAP_EASE.smooth },
} as const;

type AnimTiming = keyof typeof animConfigs;

// Stagger configurations for cascading animations
export const staggerConfig = {
  tight: 0.05,
  normal: 0.1,
  loose: 0.15,
  veryLoose: 0.2,
} as const;

// Simple animation states
export const animationStates = {
  hidden: { opacity: 0, y: -8, scale: 0.98 },
  visible: { opacity: 1, y: 0, scale: 1 },
  exit: { opacity: 0, y: -4, scale: 0.98 },
} as const;

// Simple visibility animation
export function animateVisibility(
  element: HTMLElement,
  show: boolean,
  options: {
    timing?: AnimTiming;
    onComplete?: () => void;
  } = {}
) {
  const { timing = 'fast', onComplete } = options;
  const config = animConfigs[timing];

  if (show) {
    gsap.set(element, { display: 'block' });
    return gsap.to(element, {
      ...animationStates.visible,
      ...config,
      onComplete,
    });
  } else {
    return gsap.to(element, {
      ...animationStates.exit,
      ...config,
      onComplete: () => {
        gsap.set(element, { display: 'none' });
        onComplete?.();
      },
    });
  }
}

// Animate container height smoothly
export function animateContainerHeight(
  container: HTMLElement,
  timing: AnimTiming = 'normal'
) {
  const config = animConfigs[timing];
  const children = Array.from(container.children) as HTMLElement[];

  let totalHeight = 0;
  children.forEach(child => {
    if (child.style.display !== 'none' && child.style.opacity !== '0') {
      totalHeight += child.offsetHeight + parseInt(getComputedStyle(child).marginBottom || '0');
    }
  });

  return gsap.to(container, {
    height: totalHeight,
    ...config,
  });
}

// Simple fade animation for state changes
export function fadeTransition(
  element: HTMLElement,
  timing: AnimTiming = 'fast'
) {
  const config = animConfigs[timing];

  return gsap.fromTo(
    element,
    { opacity: 0 },
    {
      opacity: 1,
      ...config,
    }
  );
}

// Simple auto-hide functionality
export function createAutoHide(
  element: HTMLElement,
  delay: number = 10000,
  onHide?: () => void
) {
  let timer: ReturnType<typeof setTimeout> | null = null;

  const start = () => {
    cancel();
    timer = setTimeout(() => {
      animateVisibility(element, false, {
        onComplete: onHide,
      });
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
