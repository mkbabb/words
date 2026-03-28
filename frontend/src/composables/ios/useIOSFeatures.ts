import { ref, onMounted, onUnmounted, type ComputedRef } from 'vue';
import { logger } from '@/utils/logger';

/**
 * Provides iOS/PWA platform features: install prompt, status bar, badge, share, haptics.
 *
 * @param supportsBadging - Computed ref for badge API support.
 * @param supportsShare   - Computed ref for Web Share API support.
 * @param supportsVibrate - Computed ref for Vibration API support.
 */
export function useIOSFeatures(
  supportsBadging: ComputedRef<boolean>,
  supportsShare: ComputedRef<boolean>,
  supportsVibrate: ComputedRef<boolean>,
) {
  // Install prompt state
  const canInstall = ref(false);
  const deferredPrompt = ref<any>(null);

  let handleBeforeInstallPrompt: ((e: any) => void) | null = null;

  onMounted(() => {
    handleBeforeInstallPrompt = (e: any) => {
      e.preventDefault();
      deferredPrompt.value = e;
      canInstall.value = true;
    };
    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
  });

  onUnmounted(() => {
    if (handleBeforeInstallPrompt) {
      window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    }
  });

  // Status bar handling
  function setStatusBarStyle(style: 'default' | 'black' | 'black-translucent') {
    const meta = document.querySelector(
      'meta[name="apple-mobile-web-app-status-bar-style"]',
    );
    if (meta) {
      meta.setAttribute('content', style);
    }
  }

  // App badge support
  async function setAppBadge(count?: number) {
    if (!supportsBadging.value) return;

    try {
      if (count === undefined || count === 0) {
        await (navigator as any).clearAppBadge();
      } else {
        await (navigator as any).setAppBadge(count);
      }
    } catch (error) {
      logger.error('Failed to set app badge:', error);
    }
  }

  // Share functionality
  async function share(data: ShareData): Promise<boolean> {
    if (!supportsShare.value) return false;

    try {
      await navigator.share(data);
      return true;
    } catch (error) {
      if ((error as Error).name !== 'AbortError') {
        logger.error('Share failed:', error);
      }
      return false;
    }
  }

  // Haptic feedback
  function vibrate(pattern: number | number[]) {
    if (supportsVibrate.value) {
      navigator.vibrate(pattern);
    }
  }

  // Install prompt
  async function promptInstall() {
    if (!canInstall.value || !deferredPrompt.value) {
      return false;
    }

    try {
      deferredPrompt.value.prompt();
      const { outcome } = await deferredPrompt.value.userChoice;

      deferredPrompt.value = null;
      canInstall.value = false;

      return outcome === 'accepted';
    } catch (error) {
      logger.error('Install prompt error:', error);
      return false;
    }
  }

  return {
    canInstall,
    promptInstall,
    setStatusBarStyle,
    setAppBadge,
    share,
    vibrate,
  };
}
