# iOS PWA Implementation Guide for 2025

## Overview

This guide provides comprehensive patterns and code snippets for implementing Progressive Web Apps on iOS devices with the latest features available in iOS 17+ and Safari 17+.

## 1. iOS 17+ PWA Improvements

### New Features in iOS 17+
- **Web Push Notifications**: Finally supported on iOS (requires user permission)
- **Badging API**: Update app icon badges
- **Web Share API Level 2**: Share files and more content types
- **Screen Wake Lock**: Keep screen on during critical tasks
- **Improved Offline Support**: Better service worker reliability

### Implementation Example:

```typescript
// Check for iOS 17+ features
const checkiOS17Features = () => {
  return {
    pushSupported: 'PushManager' in window && 'serviceWorker' in navigator,
    badgingSupported: 'setAppBadge' in navigator,
    shareLevel2: 'canShare' in navigator,
    wakeLockSupported: 'wakeLock' in navigator
  };
};
```

## 2. Standalone Mode Detection

```typescript
// Comprehensive standalone detection
export const detectStandaloneMode = () => {
  // iOS Safari
  const iosStandalone = ('standalone' in navigator && (navigator as any).standalone);
  
  // Display mode media query
  const displayModeStandalone = window.matchMedia('(display-mode: standalone)').matches;
  
  // Fullscreen mode
  const fullscreen = window.matchMedia('(display-mode: fullscreen)').matches;
  
  // Minimal UI (older iOS)
  const minimalUI = window.matchMedia('(display-mode: minimal-ui)').matches;
  
  return {
    isStandalone: iosStandalone || displayModeStandalone || fullscreen,
    displayMode: getDisplayMode(),
    isIOS: /iPad|iPhone|iPod/.test(navigator.userAgent)
  };
};

const getDisplayMode = () => {
  if (window.matchMedia('(display-mode: fullscreen)').matches) return 'fullscreen';
  if (window.matchMedia('(display-mode: standalone)').matches) return 'standalone';
  if (window.matchMedia('(display-mode: minimal-ui)').matches) return 'minimal-ui';
  return 'browser';
};
```

## 3. Viewport-fit Strategies

```html
<!-- index.html -->
<meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover, user-scalable=no">
```

```css
/* Safe area handling for notched devices */
.app-container {
  /* Use env() with fallbacks */
  padding-top: env(safe-area-inset-top, 20px);
  padding-right: env(safe-area-inset-right, 0);
  padding-bottom: env(safe-area-inset-bottom, 0);
  padding-left: env(safe-area-inset-left, 0);
}

/* Dynamic Island support (iPhone 14 Pro+) */
@supports (top: constant(safe-area-inset-top)) {
  .header {
    padding-top: max(
      constant(safe-area-inset-top),
      env(safe-area-inset-top),
      20px
    );
  }
}

/* Landscape orientation handling */
@media (orientation: landscape) {
  .app-container {
    padding-left: max(env(safe-area-inset-left), 44px);
    padding-right: max(env(safe-area-inset-right), 44px);
  }
}
```

## 4. Status Bar Customization

```html
<!-- Status bar styles -->
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<!-- Options: default | black | black-translucent -->
```

```typescript
// Dynamic status bar color based on theme
export const updateStatusBar = (theme: 'light' | 'dark') => {
  const metaTag = document.querySelector('meta[name="apple-mobile-web-app-status-bar-style"]');
  if (metaTag) {
    metaTag.setAttribute('content', theme === 'dark' ? 'black-translucent' : 'default');
  }
  
  // Update theme color too
  const themeColor = document.querySelector('meta[name="theme-color"]');
  if (themeColor) {
    themeColor.setAttribute('content', theme === 'dark' ? '#000000' : '#ffffff');
  }
};
```

## 5. Touch Icons and Splash Screens

```html
<!-- Touch icons for various devices -->
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="apple-touch-icon" sizes="152x152" href="/apple-touch-icon-152x152.png">
<link rel="apple-touch-icon" sizes="167x167" href="/apple-touch-icon-167x167.png">

<!-- Splash screens for different devices -->
<!-- iPhone 14 Pro Max -->
<link rel="apple-touch-startup-image" 
      media="(device-width: 430px) and (device-height: 932px) and (-webkit-device-pixel-ratio: 3)" 
      href="/splash/iphone14promax.png">

<!-- iPhone 14 Pro -->
<link rel="apple-touch-startup-image" 
      media="(device-width: 393px) and (device-height: 852px) and (-webkit-device-pixel-ratio: 3)" 
      href="/splash/iphone14pro.png">

<!-- iPad Pro 12.9" -->
<link rel="apple-touch-startup-image" 
      media="(device-width: 1024px) and (device-height: 1366px) and (-webkit-device-pixel-ratio: 2)" 
      href="/splash/ipadpro129.png">
```

### Splash Screen Generator Script:

```typescript
// Generate splash screens for all iOS devices
import sharp from 'sharp';

const devices = [
  { name: 'iphone14promax', width: 1290, height: 2796 },
  { name: 'iphone14pro', width: 1179, height: 2556 },
  { name: 'iphone14', width: 1170, height: 2532 },
  { name: 'iphone13mini', width: 1125, height: 2436 },
  { name: 'ipadpro129', width: 2048, height: 2732 },
  { name: 'ipadpro11', width: 1668, height: 2388 }
];

export async function generateSplashScreens(logoPath: string, backgroundColor: string) {
  for (const device of devices) {
    await sharp({
      create: {
        width: device.width,
        height: device.height,
        channels: 4,
        background: backgroundColor
      }
    })
    .composite([{
      input: logoPath,
      gravity: 'centre'
    }])
    .png()
    .toFile(`./public/splash/${device.name}.png`);
  }
}
```

## 6. iOS-Specific Meta Tags

```html
<!-- Complete set of iOS meta tags -->
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-title" content="Your App Name">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="format-detection" content="telephone=no">
<meta name="apple-touch-fullscreen" content="yes">

<!-- Disable auto-detection of addresses -->
<meta name="format-detection" content="address=no">

<!-- Disable auto-detection of dates -->
<meta name="format-detection" content="date=no">

<!-- Disable auto-detection of email addresses -->
<meta name="format-detection" content="email=no">
```

## 7. Gesture Navigation

```typescript
// Comprehensive gesture handling
export class IOSGestureHandler {
  private touchStartX = 0;
  private touchStartY = 0;
  private touchStartTime = 0;
  
  constructor(
    private onSwipeLeft?: () => void,
    private onSwipeRight?: () => void,
    private onSwipeUp?: () => void,
    private onSwipeDown?: () => void,
    private onPullToRefresh?: () => Promise<void>
  ) {
    this.init();
  }
  
  private init() {
    // Edge swipe for navigation
    document.addEventListener('touchstart', this.handleTouchStart.bind(this), { passive: true });
    document.addEventListener('touchmove', this.handleTouchMove.bind(this), { passive: false });
    document.addEventListener('touchend', this.handleTouchEnd.bind(this), { passive: true });
  }
  
  private handleTouchStart(e: TouchEvent) {
    this.touchStartX = e.touches[0].clientX;
    this.touchStartY = e.touches[0].clientY;
    this.touchStartTime = Date.now();
  }
  
  private handleTouchMove(e: TouchEvent) {
    if (!this.touchStartY) return;
    
    const currentY = e.touches[0].clientY;
    const deltaY = currentY - this.touchStartY;
    
    // Pull to refresh detection
    if (window.scrollY === 0 && deltaY > 50 && this.onPullToRefresh) {
      e.preventDefault();
      // Show refresh indicator
    }
  }
  
  private async handleTouchEnd(e: TouchEvent) {
    const touchEndX = e.changedTouches[0].clientX;
    const touchEndY = e.changedTouches[0].clientY;
    const deltaX = touchEndX - this.touchStartX;
    const deltaY = touchEndY - this.touchStartY;
    const deltaTime = Date.now() - this.touchStartTime;
    
    // Quick swipe detection (under 300ms)
    if (deltaTime < 300) {
      const absX = Math.abs(deltaX);
      const absY = Math.abs(deltaY);
      
      // Horizontal swipe
      if (absX > absY && absX > 50) {
        if (deltaX > 0 && this.onSwipeRight) {
          this.onSwipeRight();
        } else if (deltaX < 0 && this.onSwipeLeft) {
          this.onSwipeLeft();
        }
      }
      
      // Vertical swipe
      else if (absY > absX && absY > 50) {
        if (deltaY > 0 && this.onSwipeDown) {
          this.onSwipeDown();
        } else if (deltaY < 0 && this.onSwipeUp) {
          this.onSwipeUp();
        }
      }
    }
    
    // Pull to refresh
    if (window.scrollY === 0 && deltaY > 100 && this.onPullToRefresh) {
      await this.onPullToRefresh();
    }
  }
}
```

## 8. Camera and Sensor Access

```typescript
// iOS-optimized media capture
export class IOSMediaCapture {
  async requestCameraPermission(): Promise<boolean> {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ 
        video: { 
          facingMode: 'environment',
          width: { ideal: 1920 },
          height: { ideal: 1080 }
        } 
      });
      stream.getTracks().forEach(track => track.stop());
      return true;
    } catch (error) {
      console.error('Camera permission denied:', error);
      return false;
    }
  }
  
  async capturePhoto(facingMode: 'user' | 'environment' = 'environment'): Promise<Blob> {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { 
        facingMode,
        width: { ideal: 1920 },
        height: { ideal: 1080 }
      }
    });
    
    const video = document.createElement('video');
    video.srcObject = stream;
    video.play();
    
    await new Promise(resolve => video.onloadedmetadata = resolve);
    
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d')!;
    ctx.drawImage(video, 0, 0);
    
    stream.getTracks().forEach(track => track.stop());
    
    return new Promise(resolve => {
      canvas.toBlob(blob => resolve(blob!), 'image/jpeg', 0.9);
    });
  }
  
  // Motion sensors (iOS 13+)
  async requestMotionPermission(): Promise<boolean> {
    if ('DeviceMotionEvent' in window && 
        typeof (DeviceMotionEvent as any).requestPermission === 'function') {
      try {
        const permission = await (DeviceMotionEvent as any).requestPermission();
        return permission === 'granted';
      } catch (error) {
        console.error('Motion permission denied:', error);
        return false;
      }
    }
    return true; // Permission not required
  }
}
```

## 9. App Clips Integration

```typescript
// App Clips bridge
export class AppClipsBridge {
  private isAppClip = false;
  
  constructor() {
    this.detectAppClip();
  }
  
  private detectAppClip() {
    // Check if running as App Clip
    if ('webkit' in window && 
        'messageHandlers' in (window as any).webkit &&
        'getAppClipInvocation' in (window as any).webkit.messageHandlers) {
      this.isAppClip = true;
      this.handleAppClipInvocation();
    }
  }
  
  private async handleAppClipInvocation() {
    try {
      const invocation = await (window as any).webkit.messageHandlers
        .getAppClipInvocation.postMessage({});
      
      if (invocation?.url) {
        // Handle deep link from App Clip
        this.processDeepLink(invocation.url);
      }
    } catch (error) {
      console.error('App Clip invocation failed:', error);
    }
  }
  
  private processDeepLink(url: string) {
    // Parse and handle App Clip deep links
    const urlObj = new URL(url);
    const action = urlObj.searchParams.get('action');
    
    switch (action) {
      case 'view':
        const itemId = urlObj.searchParams.get('id');
        // Navigate to item
        break;
      case 'share':
        // Handle share action
        break;
    }
  }
  
  // Upgrade to full app
  async promptAppStoreUpgrade() {
    if (this.isAppClip && 'webkit' in window) {
      (window as any).webkit.messageHandlers.presentAppStoreOverlay?.postMessage({});
    }
  }
}
```

## 10. Shortcuts and Siri Integration

```typescript
// Siri Shortcuts integration
export class SiriShortcuts {
  // Register web app activities for Siri
  async registerActivity(activity: {
    type: string;
    title: string;
    userInfo: Record<string, any>;
    keywords: string[];
  }) {
    if (!('SiriActivity' in window)) return;
    
    try {
      const siriActivity = new (window as any).SiriActivity(
        activity.type,
        activity.title,
        activity.userInfo
      );
      
      siriActivity.keywords = activity.keywords;
      siriActivity.isEligibleForSearch = true;
      siriActivity.isEligibleForPrediction = true;
      
      await siriActivity.becomeCurrent();
    } catch (error) {
      console.error('Siri activity registration failed:', error);
    }
  }
  
  // Dynamic shortcuts for iOS home screen
  async updateDynamicShortcuts(shortcuts: Array<{
    id: string;
    title: string;
    subtitle?: string;
    url: string;
    icon?: string;
  }>) {
    if (!('setAppShortcutItems' in navigator)) return;
    
    try {
      await (navigator as any).setAppShortcutItems(
        shortcuts.map(shortcut => ({
          type: `com.yourapp.${shortcut.id}`,
          localizedTitle: shortcut.title,
          localizedSubtitle: shortcut.subtitle,
          icon: shortcut.icon,
          userInfo: { url: shortcut.url }
        }))
      );
    } catch (error) {
      console.error('Dynamic shortcuts update failed:', error);
    }
  }
}
```

## 11. iOS JavaScript APIs

```typescript
// Comprehensive iOS API feature detection
export class IOSFeatureDetection {
  static getAvailableAPIs() {
    return {
      // Media
      camera: 'mediaDevices' in navigator && 'getUserMedia' in navigator.mediaDevices,
      microphone: 'mediaDevices' in navigator,
      
      // Sensors
      accelerometer: 'Accelerometer' in window,
      gyroscope: 'Gyroscope' in window,
      magnetometer: 'Magnetometer' in window,
      deviceMotion: 'DeviceMotionEvent' in window,
      deviceOrientation: 'DeviceOrientationEvent' in window,
      
      // Storage
      indexedDB: 'indexedDB' in window,
      localStorage: 'localStorage' in window,
      sessionStorage: 'sessionStorage' in window,
      
      // Connectivity
      bluetooth: 'bluetooth' in navigator,
      nfc: 'NDEFReader' in window,
      
      // System
      battery: 'getBattery' in navigator,
      clipboard: 'clipboard' in navigator,
      contacts: 'contacts' in navigator,
      geolocation: 'geolocation' in navigator,
      notification: 'Notification' in window,
      push: 'PushManager' in window,
      share: 'share' in navigator,
      vibration: 'vibrate' in navigator,
      wakeLock: 'wakeLock' in navigator,
      
      // Display
      fullscreen: 'fullscreenEnabled' in document,
      pictureInPicture: 'pictureInPictureEnabled' in document,
      
      // PWA
      badging: 'setAppBadge' in navigator,
      beforeInstallPrompt: 'BeforeInstallPromptEvent' in window,
      
      // iOS Specific
      applePaySession: 'ApplePaySession' in window,
      touchID: 'PublicKeyCredential' in window,
      siriActivity: 'SiriActivity' in window
    };
  }
}

// Usage example
const features = IOSFeatureDetection.getAvailableAPIs();
if (features.wakeLock) {
  // Use wake lock API
}
```

## 12. iOS Workarounds

### Background Processing Workaround

```typescript
// Since iOS has limited background processing, use these strategies:

class IOSBackgroundTasks {
  private visibilityState: Document['visibilityState'] = 'visible';
  private backgroundTimer: number | null = null;
  
  constructor() {
    this.setupVisibilityHandling();
    this.setupPageLifecycle();
  }
  
  private setupVisibilityHandling() {
    document.addEventListener('visibilitychange', () => {
      this.visibilityState = document.visibilityState;
      
      if (document.visibilityState === 'hidden') {
        // App went to background
        this.startBackgroundTask();
      } else {
        // App came to foreground
        this.stopBackgroundTask();
        this.syncPendingData();
      }
    });
  }
  
  private setupPageLifecycle() {
    // Page lifecycle API for better background handling
    if ('onfreeze' in document) {
      document.addEventListener('freeze', () => {
        // Page is being frozen
        this.saveState();
      });
      
      document.addEventListener('resume', () => {
        // Page is being resumed
        this.restoreState();
      });
    }
  }
  
  private startBackgroundTask() {
    // iOS gives ~30 seconds of background execution
    this.backgroundTimer = window.setTimeout(() => {
      this.saveState();
    }, 25000); // Save state before iOS suspends
  }
  
  private stopBackgroundTask() {
    if (this.backgroundTimer) {
      clearTimeout(this.backgroundTimer);
      this.backgroundTimer = null;
    }
  }
  
  private saveState() {
    // Save critical data to IndexedDB or localStorage
    const state = {
      timestamp: Date.now(),
      data: this.getCurrentState()
    };
    localStorage.setItem('app-state', JSON.stringify(state));
  }
  
  private restoreState() {
    const saved = localStorage.getItem('app-state');
    if (saved) {
      const state = JSON.parse(saved);
      // Restore if less than 5 minutes old
      if (Date.now() - state.timestamp < 300000) {
        this.applyState(state.data);
      }
    }
  }
  
  private getCurrentState(): any {
    // Return current app state
    return {};
  }
  
  private applyState(state: any) {
    // Apply saved state
  }
  
  private async syncPendingData() {
    // Sync any pending data when app returns to foreground
    if ('sync' in self.registration) {
      await self.registration.sync.register('background-sync');
    }
  }
}
```

### Audio Playback Workaround

```typescript
// iOS requires user interaction for audio playback
class IOSAudioHandler {
  private audioContext: AudioContext | null = null;
  private unlocked = false;
  
  async unlock() {
    if (this.unlocked) return;
    
    // Create audio context
    this.audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
    
    // Create empty buffer
    const buffer = this.audioContext.createBuffer(1, 1, 22050);
    const source = this.audioContext.createBufferSource();
    source.buffer = buffer;
    source.connect(this.audioContext.destination);
    
    // Play silent sound
    source.start(0);
    
    // Resume context if suspended
    if (this.audioContext.state === 'suspended') {
      await this.audioContext.resume();
    }
    
    this.unlocked = true;
  }
  
  // Call this on first user interaction
  async enableAudio() {
    document.addEventListener('touchstart', () => this.unlock(), { once: true });
    document.addEventListener('click', () => this.unlock(), { once: true });
  }
}
```

## 13. Testing Strategies

### Device Testing Setup

```typescript
// Comprehensive iOS PWA testing utilities
export class IOSPWATester {
  // Simulate different iOS environments
  static mockEnvironment(config: {
    device: 'iphone' | 'ipad';
    version: number;
    standalone: boolean;
    orientation: 'portrait' | 'landscape';
  }) {
    // Mock user agent
    Object.defineProperty(navigator, 'userAgent', {
      value: config.device === 'iphone' 
        ? `Mozilla/5.0 (iPhone; CPU iPhone OS ${config.version}_0 like Mac OS X)`
        : `Mozilla/5.0 (iPad; CPU OS ${config.version}_0 like Mac OS X)`,
      configurable: true
    });
    
    // Mock standalone
    Object.defineProperty(navigator, 'standalone', {
      value: config.standalone,
      configurable: true
    });
    
    // Mock viewport
    Object.defineProperty(window, 'innerWidth', {
      value: config.orientation === 'portrait' ? 390 : 844,
      configurable: true
    });
    
    Object.defineProperty(window, 'innerHeight', {
      value: config.orientation === 'portrait' ? 844 : 390,
      configurable: true
    });
  }
  
  // Test safe area insets
  static testSafeAreas() {
    const root = document.documentElement;
    const testCases = [
      { top: 44, right: 0, bottom: 34, left: 0 }, // iPhone X portrait
      { top: 0, right: 44, bottom: 21, left: 44 }, // iPhone X landscape
      { top: 20, right: 0, bottom: 0, left: 0 }, // Older iPhone
    ];
    
    testCases.forEach((insets, index) => {
      console.log(`Testing safe area case ${index + 1}:`);
      root.style.setProperty('--sat', `${insets.top}px`);
      root.style.setProperty('--sar', `${insets.right}px`);
      root.style.setProperty('--sab', `${insets.bottom}px`);
      root.style.setProperty('--sal', `${insets.left}px`);
      
      // Trigger layout recalculation
      document.body.offsetHeight;
      
      // Verify layout
      const container = document.querySelector('.app-container');
      if (container) {
        const computed = getComputedStyle(container);
        console.log('Computed padding:', {
          top: computed.paddingTop,
          right: computed.paddingRight,
          bottom: computed.paddingBottom,
          left: computed.paddingLeft
        });
      }
    });
  }
}
```

### Debugging Tools

```typescript
// iOS PWA debugging helper
export class IOSDebugger {
  private logs: Array<{ timestamp: number; type: string; data: any }> = [];
  
  constructor() {
    this.overrideConsole();
    this.setupRemoteDebugging();
  }
  
  private overrideConsole() {
    const originalLog = console.log;
    const originalError = console.error;
    
    console.log = (...args) => {
      this.logs.push({ timestamp: Date.now(), type: 'log', data: args });
      originalLog.apply(console, args);
    };
    
    console.error = (...args) => {
      this.logs.push({ timestamp: Date.now(), type: 'error', data: args });
      originalError.apply(console, args);
    };
  }
  
  private setupRemoteDebugging() {
    // Send logs to remote server for iOS debugging
    window.addEventListener('error', (event) => {
      this.sendToRemote({
        type: 'error',
        message: event.message,
        stack: event.error?.stack,
        timestamp: Date.now()
      });
    });
    
    window.addEventListener('unhandledrejection', (event) => {
      this.sendToRemote({
        type: 'unhandledRejection',
        reason: event.reason,
        timestamp: Date.now()
      });
    });
  }
  
  private async sendToRemote(data: any) {
    try {
      await fetch('/api/debug/log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      });
    } catch (error) {
      // Silently fail to avoid infinite loop
    }
  }
  
  // Export logs for analysis
  exportLogs() {
    const blob = new Blob([JSON.stringify(this.logs, null, 2)], 
      { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ios-debug-${Date.now()}.json`;
    a.click();
  }
}
```

## Best Practices Summary

1. **Always test on real devices** - Simulators don't catch all iOS quirks
2. **Use env() CSS variables** for safe area handling
3. **Implement proper gesture handling** for iOS navigation patterns
4. **Handle keyboard events carefully** to avoid viewport issues
5. **Test all orientations** including split-screen on iPads
6. **Implement offline-first** strategies for reliability
7. **Use proper meta tags** for optimal iOS integration
8. **Handle background limitations** gracefully
9. **Test with different status bar styles**
10. **Implement proper error handling** and remote debugging

## Additional Resources

- [Apple PWA Documentation](https://developer.apple.com/documentation/webkit/adding_a_web_app_manifest)
- [WebKit Feature Status](https://webkit.org/status/)
- [iOS Safari Release Notes](https://developer.apple.com/documentation/safari-release-notes/)