// PWA Service Manager with iOS-specific features
export class PWAService {
  private registration: ServiceWorkerRegistration | null = null;
  private updateAvailable = false;
  private refreshing = false;

  async init() {
    if (!('serviceWorker' in navigator)) {
      console.log('Service Workers not supported');
      return;
    }

    // Skip service worker in development to prevent caching issues
    if (import.meta.env.DEV) {
      console.log('Skipping service worker registration in development mode');
      return;
    }

    try {
      // Register service worker
      this.registration = await navigator.serviceWorker.register('/service-worker.js', {
        scope: '/'
      });

      // Check for updates
      this.registration.addEventListener('updatefound', () => {
        const newWorker = this.registration!.installing;
        if (newWorker) {
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              this.updateAvailable = true;
              this.notifyUpdateAvailable();
            }
          });
        }
      });

      // Handle controller changes
      navigator.serviceWorker.addEventListener('controllerchange', () => {
        if (!this.refreshing) {
          window.location.reload();
          this.refreshing = true;
        }
      });

      // iOS-specific: Handle app lifecycle
      this.setupIOSLifecycle();

      // Setup background sync
      await this.setupBackgroundSync();

      // Setup push notifications (if supported)
      await this.setupPushNotifications();

    } catch (error) {
      console.error('Service Worker registration failed:', error);
    }
  }

  private setupIOSLifecycle() {
    // Handle iOS-specific page lifecycle events
    if ('onpageshow' in window) {
      window.addEventListener('pageshow', (event: PageTransitionEvent) => {
        if (event.persisted) {
          // Page was restored from bfcache
          this.handlePageRestore();
        }
      });
    }

    // Handle visibility changes
    document.addEventListener('visibilitychange', () => {
      if (document.visibilityState === 'visible') {
        this.checkForUpdates();
      }
    });

    // iOS-specific: Handle app switching
    window.addEventListener('focus', () => {
      this.handleAppFocus();
    });

    window.addEventListener('blur', () => {
      this.handleAppBlur();
    });
  }

  private async setupBackgroundSync() {
    if (!('sync' in this.registration!)) {
      console.log('Background Sync not supported');
      return;
    }

    try {
      await this.registration!.sync.register('sync-searches');
      console.log('Background sync registered');
    } catch (error: unknown) {
      console.error('Background sync registration failed:', error);
    }
  }

  private async setupPushNotifications() {
    if (!('PushManager' in window)) {
      console.log('Push notifications not supported');
      return;
    }

    try {
      const permission = await Notification.requestPermission();
      if (permission === 'granted') {
        const subscription = await this.registration!.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: this.urlBase64ToUint8Array(
            process.env.VITE_VAPID_PUBLIC_KEY || ''
          )
        });
        
        // Send subscription to server
        await this.sendSubscriptionToServer(subscription);
      }
    } catch (error) {
      console.error('Push notification setup failed:', error);
    }
  }

  // Update handling
  async checkForUpdates() {
    if (this.registration) {
      try {
        await this.registration.update();
      } catch (error) {
        console.error('Update check failed:', error);
      }
    }
  }

  skipWaiting() {
    if (this.registration && this.registration.waiting) {
      this.registration.waiting.postMessage({ type: 'SKIP_WAITING' });
    }
  }

  private notifyUpdateAvailable() {
    // Emit event or call callback to notify UI
    window.dispatchEvent(new CustomEvent('pwa-update-available'));
  }

  // iOS-specific handlers
  private handlePageRestore() {
    // Refresh data when page is restored from cache
    this.checkForUpdates();
    window.dispatchEvent(new CustomEvent('pwa-page-restored'));
  }

  private handleAppFocus() {
    // App regained focus
    window.dispatchEvent(new CustomEvent('pwa-app-focus'));
  }

  private handleAppBlur() {
    // App lost focus
    window.dispatchEvent(new CustomEvent('pwa-app-blur'));
  }

  // Utility methods
  private urlBase64ToUint8Array(base64String: string) {
    const padding = '='.repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const rawData = window.atob(base64);
    const outputArray = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; ++i) {
      outputArray[i] = rawData.charCodeAt(i);
    }
    return outputArray;
  }

  private async sendSubscriptionToServer(subscription: PushSubscription) {
    try {
      const response = await fetch('/api/push/subscribe', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(subscription)
      });
      
      if (!response.ok) {
        throw new Error('Failed to send subscription to server');
      }
    } catch (error) {
      console.error('Failed to send subscription:', error);
    }
  }

  // iOS App Clips integration
  async checkAppClipInvocation() {
    if ('webkit' in window && 'messageHandlers' in (window as any).webkit) {
      try {
        // Check if launched from App Clip
        const invocation = await (window as any).webkit.messageHandlers.getAppClipInvocation.postMessage({});
        if (invocation) {
          this.handleAppClipInvocation(invocation);
        }
      } catch (error) {
        // Not in App Clip context
      }
    }
  }

  private handleAppClipInvocation(invocation: any) {
    // Handle App Clip specific logic
    console.log('App Clip invocation:', invocation);
    window.dispatchEvent(new CustomEvent('app-clip-invocation', { detail: invocation }));
  }

  // Shortcuts integration
  async updateShortcuts(shortcuts: Array<{ id: string; title: string; url: string }>) {
    if (!('setAppBadge' in navigator)) return;

    try {
      // Update dynamic shortcuts (iOS 15+)
      await (navigator as any).setAppShortcutItems(shortcuts.map(shortcut => ({
        type: `com.floridify.${shortcut.id}`,
        localizedTitle: shortcut.title,
        url: shortcut.url
      })));
    } catch (error) {
      console.error('Failed to update shortcuts:', error);
    }
  }

  // App badging
  async setBadge(count: number) {
    if ('setAppBadge' in navigator) {
      try {
        if (count > 0) {
          await (navigator as any).setAppBadge(count);
        } else {
          await (navigator as any).clearAppBadge();
        }
      } catch (error) {
        console.error('Failed to set badge:', error);
      }
    }
  }

  // Offline queue management
  async queueOfflineRequest(request: Request) {
    const db = await this.openDB();
    const transaction = db.transaction(['offline-queue'], 'readwrite');
    const store = transaction.objectStore('offline-queue');
    
    await store.add({
      url: request.url,
      method: request.method,
      headers: Object.fromEntries(request.headers.entries()),
      body: await request.text(),
      timestamp: Date.now()
    });
  }

  private async openDB(): Promise<IDBDatabase> {
    return new Promise((resolve, reject) => {
      const request = indexedDB.open('floridify-pwa', 1);
      
      request.onerror = () => reject(request.error);
      request.onsuccess = () => resolve(request.result);
      
      request.onupgradeneeded = (event) => {
        const db = (event.target as any).result;
        if (!db.objectStoreNames.contains('offline-queue')) {
          db.createObjectStore('offline-queue', { keyPath: 'id', autoIncrement: true });
        }
      };
    });
  }
}

// Export singleton instance
export const pwaService = new PWAService();