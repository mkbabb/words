/**
 * Animation utilities for Vue components
 */

import { ref, computed, onMounted, onUnmounted, type Ref } from 'vue';
import type { TypewriterOptions } from '@/types';

export interface AnimationComposable {
  isPlaying: Ref<boolean>;
  progress: Ref<number>;
  start: () => void;
  stop: () => void;
  reset: () => void;
}

/**
 * Base animation composable
 */
export function useAnimation(duration: number = 1000): AnimationComposable {
  const isPlaying = ref(false);
  const progress = ref(0);
  const startTime = ref(0);
  let animationFrame: number | null = null;

  const animate = (timestamp: number) => {
    if (!startTime.value) {
      startTime.value = timestamp;
    }

    const elapsed = timestamp - startTime.value;
    progress.value = Math.min(elapsed / duration, 1);

    if (progress.value < 1 && isPlaying.value) {
      animationFrame = requestAnimationFrame(animate);
    } else {
      isPlaying.value = false;
    }
  };

  const start = () => {
    if (!isPlaying.value) {
      isPlaying.value = true;
      startTime.value = 0;
      animationFrame = requestAnimationFrame(animate);
    }
  };

  const stop = () => {
    isPlaying.value = false;
    if (animationFrame) {
      cancelAnimationFrame(animationFrame);
      animationFrame = null;
    }
  };

  const reset = () => {
    stop();
    progress.value = 0;
    startTime.value = 0;
  };

  onUnmounted(() => {
    stop();
  });

  return {
    isPlaying,
    progress,
    start,
    stop,
    reset
  };
}

/**
 * Typewriter animation composable
 */
export function useTypewriter(text: string, options: Partial<TypewriterOptions> = {}) {
  const defaultOptions: TypewriterOptions = {
    speed: 50,
    delay: 0,
    easing: 'ease-out',
    autoplay: false,
    loop: false,
    cursorVisible: true,
    cursorChar: '|',
    pauseOnPunctuation: 100
  };

  const mergedOptions = { ...defaultOptions, ...options };
  const displayText = ref('');
  const showCursor = ref(mergedOptions.cursorVisible);
  const { isPlaying, progress, start, stop, reset } = useAnimation(text.length * mergedOptions.speed);

  const currentText = computed(() => {
    const charCount = Math.floor(progress.value * text.length);
    return text.slice(0, charCount);
  });

  // Update display text when progress changes
  const updateDisplayText = () => {
    displayText.value = currentText.value;
  };

  // Cursor blinking effect
  let cursorInterval: NodeJS.Timeout | null = null;
  const startCursorBlink = () => {
    if (mergedOptions.cursorVisible) {
      cursorInterval = setInterval(() => {
        showCursor.value = !showCursor.value;
      }, 500);
    }
  };

  const stopCursorBlink = () => {
    if (cursorInterval) {
      clearInterval(cursorInterval);
      cursorInterval = null;
    }
  };

  onMounted(() => {
    updateDisplayText();
    if (mergedOptions.autoplay) {
      start();
    }
  });

  onUnmounted(() => {
    stopCursorBlink();
  });

  return {
    displayText: computed(() => displayText.value + (showCursor.value ? mergedOptions.cursorChar : '')),
    isPlaying,
    progress,
    start: () => {
      start();
      startCursorBlink();
    },
    stop: () => {
      stop();
      stopCursorBlink();
    },
    reset: () => {
      reset();
      displayText.value = '';
      stopCursorBlink();
    }
  };
}

/**
 * Fade animation utility
 */
export function useFade(duration: number = 300) {
  const opacity = ref(0);
  const { progress, start, stop, reset } = useAnimation(duration);

  const fadeIn = () => {
    opacity.value = 0;
    start();
  };

  const fadeOut = () => {
    opacity.value = 1;
    start();
  };

  // Update opacity based on progress
  const updateOpacity = () => {
    opacity.value = progress.value;
  };

  return {
    opacity,
    fadeIn,
    fadeOut,
    updateOpacity,
    stop,
    reset
  };
}

/**
 * Slide animation utility
 */
export function useSlide(distance: number = 100, direction: 'up' | 'down' | 'left' | 'right' = 'up') {
  const transform = ref('');
  const { progress, start, stop, reset } = useAnimation(300);

  const getTransform = (prog: number) => {
    const currentDistance = distance * (1 - prog);
    switch (direction) {
      case 'up':
        return `translateY(${currentDistance}px)`;
      case 'down':
        return `translateY(-${currentDistance}px)`;
      case 'left':
        return `translateX(${currentDistance}px)`;
      case 'right':
        return `translateX(-${currentDistance}px)`;
      default:
        return '';
    }
  };

  const slideIn = () => {
    transform.value = getTransform(0);
    start();
  };

  // Update transform based on progress
  const updateTransform = () => {
    transform.value = getTransform(progress.value);
  };

  return {
    transform,
    slideIn,
    updateTransform,
    stop,
    reset
  };
}