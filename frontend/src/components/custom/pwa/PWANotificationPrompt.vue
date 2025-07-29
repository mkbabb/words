<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-500 ease-apple-spring"
      leave-active-class="transition-all duration-350 ease-apple-smooth"
      enter-from-class="opacity-0 scale-95 -translate-y-8"
      leave-to-class="opacity-0 scale-95 -translate-y-8"
    >
      <div
        v-if="showPrompt"
        class="fixed top-6 left-6 right-6 z-50 max-w-md mx-auto"
      >
        <div
          class="cartoon-shadow-md rounded-2xl bg-background/95 backdrop-blur-xl 
                 border-2 border-border p-6 space-y-4 texture-paper-clean
                 hover-lift transition-smooth"
        >
          <div class="flex items-start gap-4">
            <div class="rounded-xl bg-amber-100 dark:bg-amber-900/30 p-3 hover-lift-md transition-fast">
              <Bell class="h-6 w-6 text-amber-700 dark:text-amber-300 animate-wiggle-bounce" />
            </div>
            <div class="flex-1">
              <h3 class="text-lg font-semibold text-foreground">
                Daily Word Notifications
              </h3>
              <p class="text-sm text-muted-foreground mt-1">
                Get a new word delivered to you every day at 9 AM
              </p>
            </div>
            <button
              @click="dismissPrompt"
              class="p-1 rounded-lg hover:bg-muted/50 transition-fast"
            >
              <X class="h-4 w-4 text-muted-foreground" />
            </button>
          </div>
          
          <!-- Benefits -->
          <div class="space-y-2 pl-14">
            <div class="flex items-center gap-2 text-sm text-muted-foreground">
              <Sparkles class="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <span>Expand your vocabulary effortlessly</span>
            </div>
            <div class="flex items-center gap-2 text-sm text-muted-foreground">
              <BookOpen class="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <span>Learn fascinating word origins</span>
            </div>
            <div class="flex items-center gap-2 text-sm text-muted-foreground">
              <Clock class="h-4 w-4 text-amber-600 dark:text-amber-400" />
              <span>Perfect timing for your morning routine</span>
            </div>
          </div>
          
          <!-- iOS-specific message -->
          <div v-if="isIOS && !isInstalled" 
               class="p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
            <p class="text-xs text-amber-800 dark:text-amber-200 flex items-center gap-2">
              <Info class="h-3 w-3 flex-shrink-0" />
              Please install the app first to enable notifications on iOS
            </p>
          </div>
          
          <!-- Actions -->
          <div class="flex gap-3">
            <button
              @click="enableNotifications"
              :disabled="isIOS && !isInstalled"
              class="flex-1 px-4 py-3 rounded-xl bg-primary text-primary-foreground
                     font-medium transition-smooth disabled:opacity-50
                     disabled:cursor-not-allowed"
              :class="!(isIOS && !isInstalled) && 'hover-lift cartoon-shadow-sm active-scale'"
            >
              <Bell class="h-4 w-4 inline mr-2" />
              Enable Notifications
            </button>
            <button
              @click="dismissPrompt"
              class="px-4 py-3 rounded-xl border-2 border-border
                     text-foreground hover-lift transition-smooth
                     hover:bg-muted/50 active-scale"
            >
              Maybe later
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { Bell, X, Sparkles, BookOpen, Clock, Info } from 'lucide-vue-next';
import { useIOSPWA, usePWA } from '@/composables';
import { useAppStore } from '@/stores';

const store = useAppStore();
const { isIOS, isInstalled } = useIOSPWA();
const { subscribeToPush, notificationPermission } = usePWA();

const showPrompt = ref(false);

const dismissPrompt = () => {
  showPrompt.value = false;
  // Show again after 14 days
  localStorage.setItem('notification-prompt-dismissed', Date.now().toString());
};

const enableNotifications = async () => {
  // Check current permission state
  if (Notification.permission === 'denied') {
    store.showNotification({
      type: 'error',
      message: 'Notifications are blocked. Please enable them in your browser settings.'
    });
    
    // Show instructions
    const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
    if (isChrome) {
      store.showNotification({
        type: 'info',
        message: 'Click the lock icon in the address bar → Site settings → Notifications → Allow'
      });
    }
    return;
  }
  
  // Show loading state
  store.showNotification({
    type: 'info',
    message: 'Requesting notification permission...'
  });
  
  const success = await subscribeToPush();
  
  if (success) {
    showPrompt.value = false;
    store.showNotification({
      type: 'success',
      message: 'Notifications enabled! You\'ll receive your first word tomorrow.'
    });
    
    // Track in local storage
    localStorage.setItem('notifications-enabled', 'true');
  } else {
    if (Notification.permission === 'denied') {
      store.showNotification({
        type: 'error',
        message: 'Notifications blocked. Enable in browser settings and refresh the page.'
      });
    } else {
      store.showNotification({
        type: 'error',
        message: 'Could not enable notifications. Please try again.'
      });
    }
  }
};

// Check if should show notification prompt
const checkShouldShowPrompt = () => {
  // Already have permission
  if (notificationPermission.value === 'granted') return false;
  
  // Already denied
  if (notificationPermission.value === 'denied') return false;
  
  // Check if dismissed recently
  const dismissed = localStorage.getItem('notification-prompt-dismissed');
  if (dismissed) {
    const dismissedTime = parseInt(dismissed);
    const daysSince = (Date.now() - dismissedTime) / (1000 * 60 * 60 * 24);
    if (daysSince < 14) return false;
  }
  
  // Check user engagement
  const searchCount = parseInt(localStorage.getItem('search-count') || '0');
  const hasViewedDefinitions = parseInt(localStorage.getItem('definitions-viewed') || '0');
  
  // Show after meaningful engagement
  return searchCount >= 5 && hasViewedDefinitions >= 3;
};

onMounted(() => {
  // Check if should show after delay
  setTimeout(() => {
    if (checkShouldShowPrompt()) {
      // Additional delay if install prompt is showing
      const installPromptShowing = document.querySelector('[data-pwa-install-prompt]');
      const delay = installPromptShowing ? 5000 : 0;
      
      setTimeout(() => {
        showPrompt.value = true;
      }, delay);
    }
  }, 60000); // Check after 1 minute
  
  // Track definition views
  window.addEventListener('definition-viewed', () => {
    const count = parseInt(localStorage.getItem('definitions-viewed') || '0');
    localStorage.setItem('definitions-viewed', (count + 1).toString());
  });
  
  // Listen for debug show notification prompt event
  window.addEventListener('show-notification-prompt', () => {
    showPrompt.value = true;
  });
});
</script>