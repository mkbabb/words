<template>
    <div
        :class="{ ios: isIOS, 'ios-standalone': isStandalone }"
        class="min-h-screen bg-background text-foreground"
        :style="appStyles"
    >
        <router-view />
        <Toaster />
        <PWAInstallPrompt />
        <PWANotificationPrompt />
        <NotificationToast />
    </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, watch } from 'vue';
import { useUIStore } from '@/stores/ui/ui-state';
import { Toaster } from '@/components/ui/toast';
import { PWAInstallPrompt, PWANotificationPrompt } from '@/components/custom/pwa';
import NotificationToast from '@/components/custom/NotificationToast.vue';
import { useIOSPWA, usePWA } from '@/composables';
import { useStateSync } from '@/composables/useStateSync';

// Sync UIStore resolvedTheme to <html> class (single source of truth)
// Note: { immediate: true } is intentionally omitted to prevent FOUC.
// The inline script in index.html applies the initial dark class from localStorage
// before Vue mounts. Using immediate here would flash light mode because the store
// initializes with DEFAULT_THEME before persistence restores the saved value.
const ui = useUIStore();
watch(() => ui.resolvedTheme, (theme) => {
    document.documentElement.classList.toggle('dark', theme === 'dark');
});

// Initialize PWA features
const { isIOS, isStandalone, handleSwipeNavigation, handleViewportResize } = useIOSPWA();
const { registerServiceWorker } = usePWA();

// Initialize state sync (preferences + history ↔ backend)
useStateSync();

// Add subtle paper texture to main background - simplified approach
// App styles - only use background properties, not opacity/blend on the main container
const appStyles = computed(() => ({
    backgroundImage: 'var(--paper-clean-texture)',
    backgroundAttachment: 'fixed',
    backgroundSize: '60px 60px',
}));

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
