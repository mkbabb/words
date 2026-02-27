import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useEventListener } from '@vueuse/core';
import { logger } from '@/utils/logger';

export interface SafeAreaInsets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export function useIOSPWA() {
  // Device detection
  const isIOS = ref(false);
  const isIPadOS = ref(false);
  const isInstalled = ref(false);
  const isStandalone = ref(false);
  const supportsPWA = ref(false);
  const supportsNotifications = ref(false);
  
  // Install prompt state
  const canInstall = ref(false);
  const deferredPrompt = ref<any>(null);
  
  // Safe area handling
  const safeAreaInsets = ref<SafeAreaInsets>({ 
    top: 0, 
    bottom: 0, 
    left: 0, 
    right: 0 
  });
  
  // Device type detection
  const isIPhone = computed(() => /iPhone/.test(navigator.userAgent));
  const isIPad = computed(() => /iPad/.test(navigator.userAgent) || isIPadOS.value);
  const isSafari = computed(() => /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent));
  
  // iOS version detection
  const iOSVersion = computed(() => {
    if (!isIOS.value) return null;
    const match = navigator.userAgent.match(/OS (\d+)_(\d+)_?(\d+)?/);
    if (match) {
      return {
        major: parseInt(match[1], 10),
        minor: parseInt(match[2], 10),
        patch: match[3] ? parseInt(match[3], 10) : 0
      };
    }
    return null;
  });
  
  // Feature support
  const supportsBackgroundSync = computed(() => 'sync' in ServiceWorkerRegistration.prototype);
  const supportsPeriodicSync = computed(() => 'periodicSync' in ServiceWorkerRegistration.prototype);
  const supportsBadging = computed(() => 'setAppBadge' in navigator);
  const supportsShare = computed(() => 'share' in navigator);
  const supportsVibrate = computed(() => 'vibrate' in navigator);
  
  // Initialize detection
  onMounted(() => {
    // Detect iOS
    isIOS.value = /iPhone|iPad|iPod/.test(navigator.userAgent) && !(window as any).MSStream;
    
    // Detect iPadOS 13+ (reports as macOS in user agent)
    if (navigator.maxTouchPoints > 2 && /MacIntel/.test(navigator.platform)) {
      isIPadOS.value = true;
      isIOS.value = true;
    }
    
    // Check if installed as PWA
    isStandalone.value = window.matchMedia('(display-mode: standalone)').matches;
    isInstalled.value = isStandalone.value || (window.navigator as any).standalone === true;
    
    // Check PWA support
    supportsPWA.value = 'serviceWorker' in navigator;
    
    // Check notification support (iOS 16.4+)
    supportsNotifications.value = 'Notification' in window && 
      'PushManager' in window && 
      'serviceWorker' in navigator;
    
    // Get safe area insets
    updateSafeAreaInsets();
    
    // Update on orientation change
    useEventListener('orientationchange', updateSafeAreaInsets);
    useEventListener('resize', handleViewportResize);
    
    // Listen for install prompt
    window.addEventListener('beforeinstallprompt', (e: any) => {
      e.preventDefault();
      deferredPrompt.value = e;
      canInstall.value = true;
    });
  });
  
  // Update safe area insets
  function updateSafeAreaInsets() {
    const computedStyle = getComputedStyle(document.documentElement);
    safeAreaInsets.value = {
      top: parseInt(computedStyle.getPropertyValue('--sat') || 
        computedStyle.getPropertyValue('env(safe-area-inset-top)') || '0'),
      bottom: parseInt(computedStyle.getPropertyValue('--sab') || 
        computedStyle.getPropertyValue('env(safe-area-inset-bottom)') || '0'),
      left: parseInt(computedStyle.getPropertyValue('--sal') || 
        computedStyle.getPropertyValue('env(safe-area-inset-left)') || '0'),
      right: parseInt(computedStyle.getPropertyValue('--sar') || 
        computedStyle.getPropertyValue('env(safe-area-inset-right)') || '0')
    };
  }
  
  // Handle iOS viewport height changes
  function handleViewportResize() {
    if (isIOS.value) {
      // Fix for iOS Safari's dynamic viewport
      const vh = window.innerHeight * 0.01;
      document.documentElement.style.setProperty('--vh', `${vh}px`);
      
      // Update safe areas
      updateSafeAreaInsets();
    }
  }
  
  // Keyboard handling for iOS
  const keyboardHeight = ref(0);
  const isKeyboardVisible = computed(() => keyboardHeight.value > 0);
  
  function detectKeyboard() {
    if (!isIOS.value) return;
    
    const viewport = window.visualViewport;
    if (viewport) {
      viewport.addEventListener('resize', () => {
        const hasKeyboard = window.innerHeight > viewport.height;
        keyboardHeight.value = hasKeyboard ? window.innerHeight - viewport.height : 0;
      });
    }
  }
  
  onMounted(detectKeyboard);
  
  // Swipe navigation handling
  const swipeThreshold = 50;
  let touchStartX = 0;
  let touchStartY = 0;
  
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
  
  // Pull to refresh implementation
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
    
    onUnmounted(() => {
      document.removeEventListener('touchstart', handlePullStart);
      document.removeEventListener('touchmove', handlePullMove);
    });
  }
  
  // Status bar handling
  function setStatusBarStyle(style: 'default' | 'black' | 'black-translucent') {
    const meta = document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]');
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
      // Show the install prompt
      deferredPrompt.value.prompt();
      
      // Wait for the user to respond to the prompt
      const { outcome } = await deferredPrompt.value.userChoice;
      
      // Clear the deferred prompt
      deferredPrompt.value = null;
      canInstall.value = false;
      
      return outcome === 'accepted';
    } catch (error) {
      logger.error('Install prompt error:', error);
      return false;
    }
  }
  
  return {
    // Device detection
    isIOS,
    isIPadOS,
    isIPhone,
    isIPad,
    isSafari,
    isInstalled,
    isStandalone,
    iOSVersion,
    
    // Feature support
    supportsPWA,
    supportsNotifications,
    supportsBackgroundSync,
    supportsPeriodicSync,
    supportsBadging,
    supportsShare,
    supportsVibrate,
    
    // Installation
    canInstall,
    promptInstall,
    
    // Safe areas
    safeAreaInsets,
    
    // Keyboard
    keyboardHeight,
    isKeyboardVisible,
    
    // Functions
    handleSwipeNavigation,
    enablePullToRefresh,
    setStatusBarStyle,
    setAppBadge,
    share,
    vibrate,
    
    // Utilities
    handleViewportResize
  };
}