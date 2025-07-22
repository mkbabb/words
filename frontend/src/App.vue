<template>
  <div
    :class="{ dark: isDark }"
    class="bg-background text-foreground min-h-screen"
  >
    <!-- Dark Mode Toggle - Desktop only -->
    <div
      class="fixed top-0 right-0 z-50 grid items-center justify-items-center gap-2 p-2 hidden lg:grid"
    >
      <DarkModeToggle style="width: 2rem; height: 2rem" class="block" />
    </div>

    <router-view />
  </div>
</template>

<script setup lang="ts">
import { DarkModeToggle, isDark } from '@/components/custom/dark-mode-toggle';
</script>


