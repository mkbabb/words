<template>
    <div
        :class="{ dark: isDark }"
        class="min-h-screen bg-background text-foreground"
    >
        <router-view />
    </div>
</template>

<script setup lang="ts">
import { isDark } from '@/components/custom/dark-mode-toggle';
</script>
