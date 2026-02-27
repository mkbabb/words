import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useEventListener } from '@vueuse/core';
import { logger } from '@/utils/logger';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed' }>;
}

export function usePWA() {
  // Service worker state
  const isServiceWorkerSupported = ref('serviceWorker' in navigator);
  const serviceWorkerRegistration = ref<ServiceWorkerRegistration | null>(null);
  const isUpdateAvailable = ref(false);
  const isOffline = ref(!navigator.onLine);
  
  // Install prompt state
  const deferredPrompt = ref<BeforeInstallPromptEvent | null>(null);
  const isInstallable = ref(false);
  const isInstalled = ref(false);
  
  // Push notification state
  const isPushSupported = ref(false);
  const pushSubscription = ref<PushSubscription | null>(null);
  const notificationPermission = ref<NotificationPermission>('default');
  
  // VAPID public key - this will be set from environment
  const vapidPublicKey = import.meta.env.VITE_VAPID_PUBLIC_KEY || '';
  
  // Check if app is installed
  const checkInstallState = () => {
    // Check display mode
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches;
    const isMinimalUI = window.matchMedia('(display-mode: minimal-ui)').matches;
    const isFullscreen = window.matchMedia('(display-mode: fullscreen)').matches;
    
    // iOS specific check
    const isIOSStandalone = (window.navigator as any).standalone === true;
    
    isInstalled.value = isStandalone || isMinimalUI || isFullscreen || isIOSStandalone;
  };
  
  // Register service worker
  const registerServiceWorker = async () => {
    if (!isServiceWorkerSupported.value) return;
    
    // Skip service worker in development to prevent caching issues
    if (import.meta.env.DEV) {
      logger.info('Skipping service worker registration in development mode');
      return;
    }
    
    try {
      const registration = await navigator.serviceWorker.register('/service-worker.js', {
        scope: '/'
      });
      
      serviceWorkerRegistration.value = registration;
      
      // Check for updates
      registration.addEventListener('updatefound', () => {
        const newWorker = registration.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              isUpdateAvailable.value = true;
            }
          });
        }
      });
      
      // Check push support
      isPushSupported.value = 'PushManager' in window && 'Notification' in window;
      
      // Get existing subscription
      if (isPushSupported.value) {
        pushSubscription.value = await registration.pushManager.getSubscription();
        notificationPermission.value = Notification.permission;
      }
      
      logger.info('Service Worker registered successfully');
    } catch (error) {
      logger.error('Service Worker registration failed:', error);
    }
  };
  
  // Update service worker
  const updateServiceWorker = async () => {
    if (!serviceWorkerRegistration.value) return;
    
    const registration = serviceWorkerRegistration.value;
    
    // Tell waiting service worker to take control
    if (registration.waiting) {
      registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
    
    // Reload once the new service worker takes control
    let refreshing = false;
    navigator.serviceWorker.addEventListener('controllerchange', () => {
      if (!refreshing) {
        refreshing = true;
        window.location.reload();
      }
    });
  };
  
  // Install PWA
  const installApp = async () => {
    if (!deferredPrompt.value) return false;
    
    // Show the install prompt
    deferredPrompt.value.prompt();
    
    // Wait for the user's response
    const { outcome } = await deferredPrompt.value.userChoice;
    
    // Clear the deferred prompt
    deferredPrompt.value = null;
    
    // Track installation
    if (outcome === 'accepted') {
      isInstalled.value = true;
      return true;
    }
    
    return false;
  };
  
  // Subscribe to push notifications
  const subscribeToPush = async (): Promise<boolean> => {
    if (!isPushSupported.value || !serviceWorkerRegistration.value || !vapidPublicKey) {
      logger.warn('Missing requirements for push subscription');
      return false;
    }

    try {
      const permission = await Notification.requestPermission();
      notificationPermission.value = permission;

      if (permission !== 'granted') {
        logger.warn('Notification permission denied:', permission);
        return false;
      }

      const subscription = await serviceWorkerRegistration.value.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey) as Uint8Array<ArrayBuffer>
      });

      pushSubscription.value = subscription;
      
      // Send subscription to backend
      await sendSubscriptionToServer(subscription);
      
      return true;
    } catch (error) {
      logger.error('Failed to subscribe to push:', error);
      return false;
    }
  };
  
  // Unsubscribe from push
  const unsubscribeFromPush = async (): Promise<boolean> => {
    if (!pushSubscription.value) return false;
    
    try {
      await pushSubscription.value.unsubscribe();
      await removeSubscriptionFromServer(pushSubscription.value);
      pushSubscription.value = null;
      return true;
    } catch (error) {
      logger.error('Failed to unsubscribe from push:', error);
      return false;
    }
  };
  
  // Send subscription to backend
  const sendSubscriptionToServer = async (subscription: PushSubscription) => {
    try {
      const response = await fetch(`${window.location.origin}/notifications/api/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          subscription,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone
        })
      });
      
      if (!response.ok) {
        throw new Error('Failed to save subscription');
      }
    } catch (error) {
      logger.error('Failed to send subscription to server:', error);
      throw error;
    }
  };
  
  // Remove subscription from backend
  const removeSubscriptionFromServer = async (subscription: PushSubscription) => {
    try {
      await fetch(`${window.location.origin}/notifications/api/unsubscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ endpoint: subscription.endpoint })
      });
    } catch (error) {
      logger.error('Failed to remove subscription from server:', error);
    }
  };
  
  // Utility to convert VAPID key
  const urlBase64ToUint8Array = (base64String: string): Uint8Array => {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/\-/g, '+')
      .replace(/_/g, '/');
    
    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);
    
    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    
    return outputArray;
  };
  
  // Check if should show install prompt
  const shouldShowInstallPrompt = computed(() => {
    return isInstallable.value && !isInstalled.value && deferredPrompt.value !== null;
  });
  
  // Cleanup tracking
  const cleanupFns: (() => void)[] = [];

  // Initialize
  onMounted(() => {
    checkInstallState();
    registerServiceWorker();

    // Listen for beforeinstallprompt
    const handleInstallPrompt = (e: Event) => {
      e.preventDefault();
      deferredPrompt.value = e as BeforeInstallPromptEvent;
      isInstallable.value = true;
    };
    window.addEventListener('beforeinstallprompt', handleInstallPrompt);
    cleanupFns.push(() => window.removeEventListener('beforeinstallprompt', handleInstallPrompt));

    // Listen for app installed
    const handleAppInstalled = () => {
      isInstalled.value = true;
      deferredPrompt.value = null;
    };
    window.addEventListener('appinstalled', handleAppInstalled);
    cleanupFns.push(() => window.removeEventListener('appinstalled', handleAppInstalled));

    // Monitor online/offline status
    useEventListener('online', () => { isOffline.value = false; });
    useEventListener('offline', () => { isOffline.value = true; });

    // Listen for display mode changes
    const displayModeQuery = window.matchMedia('(display-mode: standalone)');
    displayModeQuery.addEventListener('change', checkInstallState);
    cleanupFns.push(() => displayModeQuery.removeEventListener('change', checkInstallState));
  });

  onUnmounted(() => {
    for (const cleanup of cleanupFns) {
      cleanup();
    }
    cleanupFns.length = 0;
  });

  return {
    // State
    isServiceWorkerSupported,
    serviceWorkerRegistration,
    isUpdateAvailable,
    isOffline,
    isInstallable,
    isInstalled,
    isPushSupported,
    pushSubscription,
    notificationPermission,
    shouldShowInstallPrompt,
    
    // Actions
    registerServiceWorker,
    updateServiceWorker,
    installApp,
    subscribeToPush,
    unsubscribeFromPush
  };
}