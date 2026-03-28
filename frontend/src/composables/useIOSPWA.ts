import { useIOSDetection } from './ios/useIOSDetection';
import { useIOSSafeArea } from './ios/useIOSSafeArea';
import { useIOSGestures } from './ios/useIOSGestures';
import { useIOSFeatures } from './ios/useIOSFeatures';

export type { SafeAreaInsets } from './ios/useIOSSafeArea';
export type { IOSVersion } from './ios/useIOSDetection';

/**
 * Unified iOS PWA composable -- backward-compatible barrel that
 * composes the four focused composables and returns a flat API.
 */
export function useIOSPWA() {
  const detection = useIOSDetection();
  const safeArea = useIOSSafeArea(detection.isIOS);
  const gestures = useIOSGestures(detection.isIOS, detection.isInstalled);
  const features = useIOSFeatures(
    detection.supportsBadging,
    detection.supportsShare,
    detection.supportsVibrate,
  );

  return {
    // Device detection
    isIOS: detection.isIOS,
    isIPadOS: detection.isIPadOS,
    isIPhone: detection.isIPhone,
    isIPad: detection.isIPad,
    isSafari: detection.isSafari,
    isInstalled: detection.isInstalled,
    isStandalone: detection.isStandalone,
    iOSVersion: detection.iOSVersion,

    // Feature support
    supportsPWA: detection.supportsPWA,
    supportsNotifications: detection.supportsNotifications,
    supportsBackgroundSync: detection.supportsBackgroundSync,
    supportsPeriodicSync: detection.supportsPeriodicSync,
    supportsBadging: detection.supportsBadging,
    supportsShare: detection.supportsShare,
    supportsVibrate: detection.supportsVibrate,

    // Installation
    canInstall: features.canInstall,
    promptInstall: features.promptInstall,

    // Safe areas
    safeAreaInsets: safeArea.safeAreaInsets,

    // Keyboard
    keyboardHeight: gestures.keyboardHeight,
    isKeyboardVisible: gestures.isKeyboardVisible,

    // Functions
    handleSwipeNavigation: gestures.handleSwipeNavigation,
    enablePullToRefresh: gestures.enablePullToRefresh,
    setStatusBarStyle: features.setStatusBarStyle,
    setAppBadge: features.setAppBadge,
    share: features.share,
    vibrate: features.vibrate,

    // Utilities
    handleViewportResize: safeArea.handleViewportResize,
  };
}
