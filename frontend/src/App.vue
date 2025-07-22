<template>
  <div
    :class="{ dark: isDark }"
    class="bg-background text-foreground min-h-screen"
  >
    <!-- Dark Mode Toggle -->
    <div
      class="fixed top-0 right-0 z-50 grid items-center justify-items-center gap-2 p-2"
    >
      <DarkModeToggle style="width: 2rem; height: 2rem" class="hidden lg:block" />
    </div>

    <router-view />
  </div>
</template>

<script setup lang="ts">
import { DarkModeToggle, isDark } from '@/components/custom/dark-mode-toggle';
</script>


