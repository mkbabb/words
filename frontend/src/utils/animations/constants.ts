/**
 * Unified Animation Constants
 * Apple-like animation system for consistent motion design
 */

// Standard durations (in ms)
export const DURATION = {
  instant: 150,   // Micro-interactions
  fast: 250,      // Hover states, small UI changes
  normal: 350,    // Most animations
  smooth: 500,    // Page transitions, modals
  slow: 700,      // Complex orchestrated animations
} as const;

// Standard easing functions
export const EASING = {
  // Primary easings
  default: 'cubic-bezier(0.25, 0.1, 0.25, 1)',      // Most animations
  smooth: 'cubic-bezier(0.4, 0, 0.2, 1)',           // Smooth transitions
  spring: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)', // Bouncy feel
  
  // Directional easings
  easeIn: 'cubic-bezier(0.42, 0, 1, 1)',            // Enter animations
  easeOut: 'cubic-bezier(0, 0, 0.58, 1)',           // Exit animations
  
  // Specialized easings
  elastic: 'cubic-bezier(0.68, -0.6, 0.32, 1.6)',   // Playful bounces
  bounceIn: 'cubic-bezier(0.6, -0.28, 0.735, 0.045)',
  bounceOut: 'cubic-bezier(0.175, 0.885, 0.32, 1.275)',
} as const;

// Standard transform values
export const TRANSFORM = {
  hover: {
    subtle: 1.02,
    normal: 1.05,
    large: 1.1,
  },
  active: 0.97,
  enter: {
    scale: 0.95,
    translateY: 10,
    rotate: 0.5,
  },
  exit: {
    scale: 0.95,
    translateY: -10,
    opacity: 0,
  },
} as const;

// Vue transition classes
export const TRANSITION_CLASSES = {
  // Micro interactions (150ms)
  micro: {
    enterActive: 'transition-all duration-150 ease-apple-smooth',
    leaveActive: 'transition-all duration-150 ease-apple-smooth',
  },
  
  // Fast transitions (250ms)
  fast: {
    enterActive: 'transition-all duration-250 ease-apple-default',
    leaveActive: 'transition-all duration-250 ease-apple-default',
  },
  
  // Normal transitions (350ms)
  normal: {
    enterActive: 'transition-all duration-350 ease-apple-default',
    leaveActive: 'transition-all duration-350 ease-apple-default',
  },
  
  // Spring transitions (350ms with bounce)
  spring: {
    enterActive: 'transition-all duration-350 ease-apple-spring',
    leaveActive: 'transition-all duration-250 ease-apple-bounce-in',
  },
  
  // Smooth transitions (500ms)
  smooth: {
    enterActive: 'transition-all duration-500 ease-apple-smooth',
    leaveActive: 'transition-all duration-350 ease-apple-ease-out',
  },
  
  // Elastic transitions (350ms with elastic bounce)
  elastic: {
    enterActive: 'transition-all duration-350 ease-apple-elastic',
    leaveActive: 'transition-all duration-200 ease-apple-bounce-in',
  },
} as const;

// Common animation patterns
export const ANIMATION_PRESETS = {
  // Dropdown/Menu animations
  dropdown: {
    enterActiveClass: TRANSITION_CLASSES.elastic.enterActive,
    leaveActiveClass: TRANSITION_CLASSES.elastic.leaveActive,
    enterFromClass: 'opacity-0 scale-90 -translate-y-2',
    enterToClass: 'opacity-100 scale-100 translate-y-0',
    leaveFromClass: 'opacity-100 scale-100 translate-y-0',
    leaveToClass: 'opacity-0 scale-90 -translate-y-2',
  },
  
  // Modal/Dialog animations
  modal: {
    enterActiveClass: TRANSITION_CLASSES.smooth.enterActive,
    leaveActiveClass: TRANSITION_CLASSES.spring.leaveActive,
    enterFromClass: 'opacity-0 scale-90 translate-y-8',
    enterToClass: 'opacity-100 scale-100 translate-y-0',
    leaveFromClass: 'opacity-100 scale-100 translate-y-0',
    leaveToClass: 'opacity-0 scale-95 translate-y-4',
  },
  
  // Page/Content transitions
  page: {
    enterActiveClass: TRANSITION_CLASSES.smooth.enterActive,
    leaveActiveClass: TRANSITION_CLASSES.spring.leaveActive,
    enterFromClass: 'opacity-0 scale-95 translate-x-8 rotate-0.5',
    enterToClass: 'opacity-100 scale-100 translate-x-0 rotate-0',
    leaveFromClass: 'opacity-100 scale-100 translate-x-0 rotate-0',
    leaveToClass: 'opacity-0 scale-95 -translate-x-8 -rotate-0.5',
  },
  
  // Fade only transitions
  fade: {
    enterActiveClass: TRANSITION_CLASSES.fast.enterActive,
    leaveActiveClass: TRANSITION_CLASSES.fast.leaveActive,
    enterFromClass: 'opacity-0',
    enterToClass: 'opacity-100',
    leaveFromClass: 'opacity-100',
    leaveToClass: 'opacity-0',
  },
  
  // Scale transitions
  scale: {
    enterActiveClass: TRANSITION_CLASSES.spring.enterActive,
    leaveActiveClass: TRANSITION_CLASSES.spring.leaveActive,
    enterFromClass: 'opacity-0 scale-0',
    enterToClass: 'opacity-100 scale-100',
    leaveFromClass: 'opacity-100 scale-100',
    leaveToClass: 'opacity-0 scale-0',
  },
} as const;

// Tailwind class helpers
export const tw = {
  // Hover effects
  hoverLift: 'hover-lift active-scale',
  hoverLiftMd: 'hover-lift-md active-scale',
  hoverLiftLg: 'hover-lift-lg active-scale',
  
  // Transitions
  transitionMicro: 'transition-micro',
  transitionFast: 'transition-fast',
  transitionNormal: 'transition-normal',
  transitionSmooth: 'transition-smooth',
  transitionSpring: 'transition-spring',
  
  // Active states
  activeScale: 'active-scale',
} as const;