import { ref, onMounted, type Ref } from 'vue';
import { useEventListener } from '@vueuse/core';

export interface SafeAreaInsets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

/**
 * Manages iOS safe area insets and dynamic viewport height.
 *
 * @param isIOS - Reactive ref indicating whether the device is iOS.
 *                When provided, viewport resize handling is iOS-only.
 *                When omitted, safe area updates still work on any platform.
 */
export function useIOSSafeArea(isIOS?: Ref<boolean>) {
  const safeAreaInsets = ref<SafeAreaInsets>({
    top: 0,
    bottom: 0,
    left: 0,
    right: 0,
  });

  // Update safe area insets from CSS env values
  function updateSafeAreaInsets() {
    const computedStyle = getComputedStyle(document.documentElement);
    safeAreaInsets.value = {
      top: parseInt(
        computedStyle.getPropertyValue('--sat') ||
          computedStyle.getPropertyValue('env(safe-area-inset-top)') ||
          '0',
      ),
      bottom: parseInt(
        computedStyle.getPropertyValue('--sab') ||
          computedStyle.getPropertyValue('env(safe-area-inset-bottom)') ||
          '0',
      ),
      left: parseInt(
        computedStyle.getPropertyValue('--sal') ||
          computedStyle.getPropertyValue('env(safe-area-inset-left)') ||
          '0',
      ),
      right: parseInt(
        computedStyle.getPropertyValue('--sar') ||
          computedStyle.getPropertyValue('env(safe-area-inset-right)') ||
          '0',
      ),
    };
  }

  // Handle iOS viewport height changes (Safari dynamic viewport)
  function handleViewportResize() {
    if (isIOS && !isIOS.value) return;

    // Fix for iOS Safari's dynamic viewport
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);

    // Update safe areas
    updateSafeAreaInsets();
  }

  onMounted(() => {
    updateSafeAreaInsets();
    useEventListener('orientationchange', updateSafeAreaInsets);
    useEventListener('resize', handleViewportResize);
  });

  return {
    safeAreaInsets,
    updateSafeAreaInsets,
    handleViewportResize,
  };
}
