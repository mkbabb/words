import { ref, computed, onMounted, onUnmounted, type Ref } from 'vue';

/**
 * Handles iOS-specific gesture and keyboard interactions.
 *
 * @param isIOS       - Reactive ref indicating whether the device is iOS.
 * @param isInstalled - Reactive ref indicating whether the app is installed as a PWA.
 */
export function useIOSGestures(isIOS: Ref<boolean>, isInstalled: Ref<boolean>) {
  const cleanupFns: (() => void)[] = [];

  // --- Keyboard handling ---
  const keyboardHeight = ref(0);
  const isKeyboardVisible = computed(() => keyboardHeight.value > 0);

  function detectKeyboard() {
    if (!isIOS.value) return;

    const viewport = window.visualViewport;
    if (viewport) {
      const handleViewportResize = () => {
        const hasKeyboard = window.innerHeight > viewport.height;
        keyboardHeight.value = hasKeyboard ? window.innerHeight - viewport.height : 0;
      };
      viewport.addEventListener('resize', handleViewportResize);
      cleanupFns.push(() => viewport.removeEventListener('resize', handleViewportResize));
    }
  }

  onMounted(detectKeyboard);

  // --- Swipe navigation ---
  const swipeThreshold = 50;
  let touchStartX = 0;
  let touchStartY = 0;

  function handleTouchStart(e: TouchEvent) {
    touchStartX = e.touches[0].clientX;
    touchStartY = e.touches[0].clientY;
  }

  function handleTouchEnd(e: TouchEvent) {
    const touchEndX = e.changedTouches[0].clientX;
    const touchEndY = e.changedTouches[0].clientY;

    const deltaX = touchEndX - touchStartX;
    const deltaY = Math.abs(touchEndY - touchStartY);

    // Ensure horizontal swipe
    if (Math.abs(deltaX) > swipeThreshold && deltaY < swipeThreshold) {
      if (deltaX > 0 && touchStartX < 20) {
        // Swipe from left edge - go back
        window.history.back();
      } else if (deltaX < 0 && touchStartX > window.innerWidth - 20) {
        // Swipe from right edge - go forward
        window.history.forward();
      }
    }
  }

  function handleSwipeNavigation(enable = true) {
    if (!isIOS.value || !isInstalled.value) return;

    if (enable) {
      document.addEventListener('touchstart', handleTouchStart, { passive: true });
      document.addEventListener('touchend', handleTouchEnd, { passive: true });
    } else {
      document.removeEventListener('touchstart', handleTouchStart);
      document.removeEventListener('touchend', handleTouchEnd);
    }
  }

  // --- Pull to refresh ---
  const isPullToRefreshEnabled = ref(false);
  let pullStartY = 0;

  function enablePullToRefresh(onRefresh: () => void | Promise<void>) {
    if (!isIOS.value || !isInstalled.value) return;

    isPullToRefreshEnabled.value = true;

    const handlePullStart = (e: TouchEvent) => {
      if (window.scrollY === 0) {
        pullStartY = e.touches[0].clientY;
      }
    };

    const handlePullMove = async (e: TouchEvent) => {
      if (pullStartY > 0) {
        const pullDistance = e.touches[0].clientY - pullStartY;
        if (pullDistance > 100) {
          pullStartY = 0;
          await onRefresh();
        }
      }
    };

    document.addEventListener('touchstart', handlePullStart, { passive: true });
    document.addEventListener('touchmove', handlePullMove, { passive: true });

    cleanupFns.push(() => {
      document.removeEventListener('touchstart', handlePullStart);
      document.removeEventListener('touchmove', handlePullMove);
    });
  }

  // Cleanup all event listeners on unmount
  onUnmounted(() => {
    for (const cleanup of cleanupFns) {
      cleanup();
    }
    cleanupFns.length = 0;
  });

  return {
    keyboardHeight,
    isKeyboardVisible,
    handleSwipeNavigation,
    enablePullToRefresh,
  };
}
