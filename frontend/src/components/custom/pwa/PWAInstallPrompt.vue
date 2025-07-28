<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition-all duration-500 ease-apple-spring"
      leave-active-class="transition-all duration-350 ease-apple-smooth"
      enter-from-class="opacity-0 scale-95 translate-y-8"
      leave-to-class="opacity-0 scale-95 translate-y-8"
    >
      <div
        v-if="showPrompt && !isMinimized"
        class="fixed bottom-6 left-6 right-6 z-50 max-w-md mx-auto"
      >
        <div
          class="cartoon-shadow-md rounded-2xl bg-background/95 backdrop-blur-xl 
                 border-2 border-border p-6 space-y-4 texture-paper-clean
                 hover-lift transition-smooth"
        >
          <!-- iOS-specific instructions -->
          <div v-if="isIOS && !isInstalled" class="space-y-4">
            <div class="flex items-center gap-4">
              <div class="rounded-xl bg-primary/10 p-3 hover-lift-md transition-fast">
                <Share2 class="h-6 w-6 text-primary animate-wiggle" />
              </div>
              <div class="flex-1">
                <h3 class="text-lg font-semibold text-foreground">
                  Install Floridify
                </h3>
                <p class="text-sm text-muted-foreground">
                  Add to your home screen for the best experience
                </p>
              </div>
              <button
                @click="minimize"
                class="p-1 rounded-lg hover:bg-muted/50 transition-fast"
                title="Minimize"
              >
                <Minus class="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
            
            <div class="space-y-3 text-sm">
              <div 
                v-for="(step, index) in iosSteps" 
                :key="index"
                class="flex items-center gap-3 group"
              >
                <div 
                  class="flex-shrink-0 w-8 h-8 rounded-full bg-primary/20 
                         flex items-center justify-center text-xs font-semibold
                         group-hover:scale-110 group-hover:bg-primary/30 transition-fast"
                  :class="`delay-${index * 150}`"
                >
                  {{ index + 1 }}
                </div>
                <p class="flex items-center gap-2" v-html="step"></p>
              </div>
            </div>
            
            <div class="flex gap-3">
              <button
                @click="dismissPrompt"
                class="flex-1 px-4 py-2 rounded-xl border-2 border-border
                       text-foreground hover-lift transition-smooth
                       hover:bg-muted/50 active-scale"
              >
                Maybe later
              </button>
              <button
                @click="dismissPromptPermanently"
                class="px-4 py-2 rounded-xl text-muted-foreground
                       hover:text-foreground transition-smooth"
              >
                Don't show again
              </button>
            </div>
          </div>
          
          <!-- Android/Desktop prompt -->
          <div v-else-if="shouldShowInstallPrompt" class="space-y-4">
            <div class="flex items-center gap-4">
              <div class="rounded-xl bg-primary/10 p-3 hover-lift-md transition-fast">
                <Download class="h-6 w-6 text-primary animate-bounce-in" />
              </div>
              <div class="flex-1">
                <h3 class="text-lg font-semibold text-foreground">
                  Install Floridify
                </h3>
                <p class="text-sm text-muted-foreground">
                  Install our app for offline access and daily word notifications
                </p>
              </div>
              <button
                @click="minimize"
                class="p-1 rounded-lg hover:bg-muted/50 transition-fast"
                title="Minimize"
              >
                <Minus class="h-4 w-4 text-muted-foreground" />
              </button>
            </div>
            
            <div class="space-y-2">
              <div class="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle2 class="h-4 w-4 text-green-600 dark:text-green-400" />
                <span>Works offline</span>
              </div>
              <div class="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle2 class="h-4 w-4 text-green-600 dark:text-green-400" />
                <span>Daily word notifications</span>
              </div>
              <div class="flex items-center gap-2 text-sm text-muted-foreground">
                <CheckCircle2 class="h-4 w-4 text-green-600 dark:text-green-400" />
                <span>Faster loading</span>
              </div>
            </div>
            
            <div class="flex gap-3">
              <button
                @click="installPWA"
                class="flex-1 px-4 py-3 rounded-xl bg-primary text-primary-foreground
                       font-medium hover-lift cartoon-shadow-sm transition-smooth
                       active-scale"
              >
                Install App
              </button>
              <button
                @click="dismissPrompt"
                class="px-4 py-3 rounded-xl border-2 border-border
                       text-foreground hover-lift transition-smooth
                       hover:bg-muted/50 active-scale"
              >
                Not now
              </button>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Minimized state -->
    <Transition
      enter-active-class="transition-all duration-350 ease-apple-spring"
      leave-active-class="transition-all duration-250 ease-apple-smooth"
      enter-from-class="opacity-0 scale-90"
      leave-to-class="opacity-0 scale-90"
    >
      <button
        v-if="showPrompt && isMinimized"
        @click="restore"
        class="fixed bottom-6 right-6 z-50 p-3 rounded-full
               bg-primary text-primary-foreground cartoon-shadow-sm
               hover-lift hover:scale-110 transition-smooth active-scale"
        title="Show install prompt"
      >
        <Download class="h-5 w-5" />
      </button>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { Share2, Download, Minus, CheckCircle2 } from 'lucide-vue-next';
import { useIOSPWA, usePWA } from '@/composables';
import { useAppStore } from '@/stores';

const store = useAppStore();
const { isIOS, isInstalled } = useIOSPWA();
const { shouldShowInstallPrompt, installApp } = usePWA();

const showPrompt = ref(false);
const isMinimized = ref(false);

// iOS installation steps with icons
const iosSteps = [
  'Tap the <svg class="inline h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path><polyline points="16 6 12 2 8 6"></polyline><line x1="12" y1="2" x2="12" y2="15"></line></svg> share button below',
  'Scroll down and tap "Add to Home Screen"',
  'Tap "Add" to install'
];

const dismissPrompt = () => {
  showPrompt.value = false;
  isMinimized.value = false;
  // Show again after 7 days
  localStorage.setItem('pwa-prompt-dismissed', Date.now().toString());
};

const dismissPromptPermanently = () => {
  showPrompt.value = false;
  isMinimized.value = false;
  localStorage.setItem('pwa-prompt-dismissed', 'permanent');
};

const minimize = () => {
  isMinimized.value = true;
};

const restore = () => {
  isMinimized.value = false;
};

const installPWA = async () => {
  const success = await installApp();
  if (success) {
    showPrompt.value = false;
    // Show success notification
    store.showNotification({
      type: 'success',
      message: 'App installed successfully!'
    });
  }
};

// Check if should show prompt based on engagement
const checkEngagement = () => {
  // Check if dismissed
  const dismissed = localStorage.getItem('pwa-prompt-dismissed');
  if (dismissed === 'permanent') return false;
  
  if (dismissed) {
    const dismissedTime = parseInt(dismissed);
    const daysSince = (Date.now() - dismissedTime) / (1000 * 60 * 60 * 24);
    if (daysSince < 7) return false;
  }
  
  // Check engagement metrics
  const searchCount = parseInt(localStorage.getItem('search-count') || '0');
  const sessionTime = Date.now() - (store.sessionStartTime || Date.now());
  
  // Show after 3 searches or 2 minutes of engagement
  return searchCount >= 3 || sessionTime > 120000;
};

// Store interval ID outside to clear it later
let checkInterval: ReturnType<typeof setInterval> | null = null;

onMounted(() => {
  // iOS prompt logic
  if (isIOS.value && !isInstalled.value) {
    // Check engagement periodically
    checkInterval = setInterval(() => {
      if (checkEngagement()) {
        showPrompt.value = true;
        if (checkInterval) clearInterval(checkInterval);
      }
    }, 10000); // Check every 10 seconds
  }
  
  // Android/Desktop prompt handled by shouldShowInstallPrompt
  if (shouldShowInstallPrompt.value) {
    setTimeout(() => {
      if (checkEngagement()) {
        showPrompt.value = true;
      }
    }, 30000); // Show after 30 seconds
  }
  
  // Track searches for engagement
  window.addEventListener('word-searched', () => {
    const count = parseInt(localStorage.getItem('search-count') || '0');
    localStorage.setItem('search-count', (count + 1).toString());
  });
  
  // Listen for debug show prompt event
  window.addEventListener('show-pwa-prompt', () => {
    showPrompt.value = true;
    isMinimized.value = false;
  });
});

// Clean up interval on unmount
onUnmounted(() => {
  if (checkInterval) {
    clearInterval(checkInterval);
  }
});
</script>