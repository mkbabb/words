import { ref, computed, onMounted } from 'vue';

export interface IOSVersion {
  major: number;
  minor: number;
  patch: number;
}

export function useIOSDetection() {
  // Device detection
  const isIOS = ref(false);
  const isIPadOS = ref(false);
  const isInstalled = ref(false);
  const isStandalone = ref(false);
  const supportsPWA = ref(false);
  const supportsNotifications = ref(false);

  // Device type detection
  const isIPhone = computed(() => /iPhone/.test(navigator.userAgent));
  const isIPad = computed(() => /iPad/.test(navigator.userAgent) || isIPadOS.value);
  const isSafari = computed(
    () => /Safari/.test(navigator.userAgent) && !/Chrome/.test(navigator.userAgent),
  );

  // iOS version detection
  const iOSVersion = computed<IOSVersion | null>(() => {
    if (!isIOS.value) return null;
    const match = navigator.userAgent.match(/OS (\d+)_(\d+)_?(\d+)?/);
    if (match) {
      return {
        major: parseInt(match[1], 10),
        minor: parseInt(match[2], 10),
        patch: match[3] ? parseInt(match[3], 10) : 0,
      };
    }
    return null;
  });

  // Feature support
  const supportsBackgroundSync = computed(
    () => 'sync' in ServiceWorkerRegistration.prototype,
  );
  const supportsPeriodicSync = computed(
    () => 'periodicSync' in ServiceWorkerRegistration.prototype,
  );
  const supportsBadging = computed(() => 'setAppBadge' in navigator);
  const supportsShare = computed(() => 'share' in navigator);
  const supportsVibrate = computed(() => 'vibrate' in navigator);

  // Initialize detection
  onMounted(() => {
    // Detect iOS
    isIOS.value =
      /iPhone|iPad|iPod/.test(navigator.userAgent) && !(window as any).MSStream;

    // Detect iPadOS 13+ (reports as macOS in user agent)
    if (navigator.maxTouchPoints > 2 && /MacIntel/.test(navigator.platform)) {
      isIPadOS.value = true;
      isIOS.value = true;
    }

    // Conditionally load iOS PWA styles
    if (isIOS.value) {
      import('../../styles/ios-pwa.css');
    }

    // Check if installed as PWA
    isStandalone.value = window.matchMedia('(display-mode: standalone)').matches;
    isInstalled.value =
      isStandalone.value || (window.navigator as any).standalone === true;

    // Check PWA support
    supportsPWA.value = 'serviceWorker' in navigator;

    // Check notification support (iOS 16.4+)
    supportsNotifications.value =
      'Notification' in window &&
      'PushManager' in window &&
      'serviceWorker' in navigator;
  });

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

    // Feature support flags
    supportsPWA,
    supportsNotifications,
    supportsBackgroundSync,
    supportsPeriodicSync,
    supportsBadging,
    supportsShare,
    supportsVibrate,
  };
}
