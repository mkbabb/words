<template>
  <div :class="{ dark: isDark }" class="min-h-screen bg-background text-foreground">
    <!-- Dark Mode Toggle -->
    <div class="fixed top-4 right-4 z-50">
      <DarkModeToggle style="width: 2rem; height: 2rem;" />
    </div>
    
    <router-view />
  </div>
</template>

<script setup lang="ts">
import { DarkModeToggle, isDark } from '@/components/custom/dark-mode-toggle';
</script>

<style>
@import '@/assets/index.css';
</style>