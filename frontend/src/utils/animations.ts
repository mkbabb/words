import { gsap } from 'gsap';

// Check for reduced motion preference
const prefersReducedMotion = () => {
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
};

// Subtle timing configurations for modern UI
export const timings = {
  instant: { duration: prefersReducedMotion() ? 0 : 0.15, ease: 'power2.out' },
  fast: { duration: prefersReducedMotion() ? 0 : 0.25, ease: 'power2.out' },
  normal: { duration: prefersReducedMotion() ? 0 : 0.35, ease: 'power3.out' },
  smooth: { duration: prefersReducedMotion() ? 0 : 0.5, ease: 'power3.inOut' },
  // Deprecated - use timings instead
  springConfig: {
    gentle: { duration: prefersReducedMotion() ? 0 : 0.5, ease: 'power3.out' },
    bouncy: { duration: prefersReducedMotion() ? 0 : 0.5, ease: 'power3.out' },
    snappy: { duration: prefersReducedMotion() ? 0 : 0.3, ease: 'power2.out' },
    smooth: { duration: prefersReducedMotion() ? 0 : 0.5, ease: 'power3.out' },
    material: { duration: prefersReducedMotion() ? 0 : 0.3, ease: 'power2.out' },
  }
} as const;

// Keep springConfig for backward compatibility
export const springConfig = timings.springConfig;

// Standard durations
export const durations = {
  instant: 0.15,
  fast: 0.25,
  normal: 0.35,
  slow: 0.5,
  verySlow: 0.8,
} as const;

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
    timing?: keyof typeof timings;
    onComplete?: () => void;
  } = {}
) {
  const { timing = 'fast', onComplete } = options;
  const config = timings[timing];
  
  if (show) {
    // Ensure element is visible first
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
  timing: keyof typeof timings = 'normal'
) {
  const config = timings[timing];
  const children = Array.from(container.children) as HTMLElement[];
  
  // Calculate total height needed
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
  timing: keyof typeof timings = 'fast'
) {
  const config = timings[timing];
  
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