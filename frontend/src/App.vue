<template>
    <div
        :class="{ dark: isDark }"
        class="min-h-screen bg-background text-foreground"
        :style="appStyles"
    >
        <router-view />
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { isDark } from '@/components/custom/dark-mode-toggle';

// Add subtle paper texture to main background - simplified approach

// App styles - only use background properties, not opacity/blend on the main container
const appStyles = computed(() => ({
    backgroundImage: 'var(--paper-clean-texture)',
    backgroundAttachment: 'fixed',
    backgroundSize: '60px 60px',
}));
</script>
