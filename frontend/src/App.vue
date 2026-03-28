<template>
    <TooltipProvider :delay-duration="200">
        <div
            :class="{ ios: isIOS, 'ios-standalone': isStandalone }"
            class="app-shell min-h-screen bg-background text-foreground"
        >
            <router-view />
            <Toaster />
            <PWAInstallPrompt />
            <PWANotificationPrompt />
            <NotificationToast />
        </div>
    </TooltipProvider>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue';
import { Toaster, TooltipProvider, useGlobalDark } from '@mkbabb/glass-ui';
import { PWAInstallPrompt, PWANotificationPrompt } from '@/components/custom/pwa';
import NotificationToast from '@/components/custom/NotificationToast.vue';
import { useIOSPWA, usePWA } from '@/composables';
import { useStateSync } from '@/composables/useStateSync';
import { useAuthProfile } from '@/composables/useAuthProfile';

// glass-ui's useGlobalDark handles dark mode class on <html> and
// suppresses CSS transitions during the swap via disableTransitions.
useGlobalDark();

// Initialize PWA features
const { isIOS, isStandalone, handleSwipeNavigation, handleViewportResize } = useIOSPWA();
const { registerServiceWorker } = usePWA();

// Initialize auth profile fetching (watches auth state)
useAuthProfile();

// Initialize state sync (preferences + history ↔ backend)
useStateSync();

// Engagement metric handlers (defined outside onMounted for proper cleanup)
const handleWordSearched = () => {
    const count = parseInt(localStorage.getItem('search-count') || '0', 10);
    if (!Number.isNaN(count)) {
        localStorage.setItem('search-count', (count + 1).toString());
    } else {
        localStorage.setItem('search-count', '1');
    }
};

const handleDefinitionViewed = () => {
    const count = parseInt(localStorage.getItem('definitions-viewed') || '0', 10);
    if (!Number.isNaN(count)) {
        localStorage.setItem('definitions-viewed', (count + 1).toString());
    } else {
        localStorage.setItem('definitions-viewed', '1');
    }
};

// Initialize PWA on mount
onMounted(async () => {
    // Register service worker
    await registerServiceWorker();

    // Setup iOS-specific features
    if (isIOS.value) {
        handleSwipeNavigation(true);
        handleViewportResize();
    }

    // Track engagement metrics with proper cleanup
    window.addEventListener('word-searched', handleWordSearched);
    window.addEventListener('definition-viewed', handleDefinitionViewed);
});

onUnmounted(() => {
    window.removeEventListener('word-searched', handleWordSearched);
    window.removeEventListener('definition-viewed', handleDefinitionViewed);
});
</script>

<style scoped>
.app-shell {
    position: relative;
    isolation: isolate;
}

.app-shell::before {
    content: '';
    position: fixed;
    inset: 0;
    z-index: -1;
    pointer-events: none;
    background-image: var(--paper-clean-texture);
    background-size: 60px 60px;
    opacity: 0.9;
}
</style>
