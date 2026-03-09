export { default as DarkModeToggle } from './DarkModeToggle.vue';

import { computed } from 'vue';
import { useUIStore } from '@/stores/ui/ui-state';
import { CSSKeyframesAnimation } from '@mkbabb/keyframes.js';

// Unified theme: UIStore is the single source of truth
const isDark = computed(() => {
  const ui = useUIStore();
  return ui.resolvedTheme === 'dark';
});

export const changeTheme = () => {
  const ui = useUIStore();
  document.documentElement.classList.add('theme-transitioning');
  ui.toggleTheme();
  setTimeout(() => {
    document.documentElement.classList.remove('theme-transitioning');
  }, 350);
};

export { isDark };

// keyframes.js animation factories
// useWAAPI: false forces rAF interpolation which is more reliable on SVG <g> elements
// than WAAPI (which can be compositor-deferred and clash with the theme class change).

const SUN_DURATION = 300;
const CIRCLE_DURATION = 200;

const sunToDarkKeyframes = /*css*/ `
  @keyframes sunToDark {
    from { transform: rotateZ(0turn); }
    to   { transform: rotateZ(0.5turn); }
  }
`;

const sunToLightKeyframes = /*css*/ `
  @keyframes sunToLight {
    from { transform: rotateZ(0.5turn); }
    to   { transform: rotateZ(0turn); }
  }
`;

const circleToDarkKeyframes = /*css*/ `
  @keyframes circleToDark {
    from { transform: translateX(0%); }
    to   { transform: translateX(-15%); }
  }
`;

const circleToLightKeyframes = /*css*/ `
  @keyframes circleToLight {
    from { transform: translateX(-15%); }
    to   { transform: translateX(0%); }
  }
`;

// Track running animations so we can cancel before starting a new one
let activeSunAnim: CSSKeyframesAnimation<any> | null = null;
let activeCircleAnim: CSSKeyframesAnimation<any> | null = null;

export const createSunAnimation = (el: HTMLElement, toDark: boolean) => {
  if (activeSunAnim?.playing()) activeSunAnim.stop();
  activeSunAnim = new CSSKeyframesAnimation({
    duration: SUN_DURATION,
    timingFunction: 'ease-in-out' as const,
    fillMode: 'forwards',
    useWAAPI: false,
  }).setTargets(el).fromString(toDark ? sunToDarkKeyframes : sunToLightKeyframes);
  return activeSunAnim;
};

export const createCircleAnimation = (el: HTMLElement, toDark: boolean) => {
  if (activeCircleAnim?.playing()) activeCircleAnim.stop();
  activeCircleAnim = new CSSKeyframesAnimation({
    duration: CIRCLE_DURATION,
    timingFunction: 'ease-out',
    fillMode: 'forwards',
    useWAAPI: false,
  }).setTargets(el).fromString(toDark ? circleToDarkKeyframes : circleToLightKeyframes);
  return activeCircleAnim;
};
