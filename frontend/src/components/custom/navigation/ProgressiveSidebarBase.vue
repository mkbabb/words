<template>
  <div 
    class="themed-card themed-shadow-lg rounded-lg bg-background/95 p-2 backdrop-blur-sm"
    :data-theme="selectedCardVariant || 'default'"
  >
    <!-- Optional Header Slot -->
    <div v-if="$slots.header" class="mb-2">
      <slot name="header" />
    </div>

    <!-- Main Content - Scrollable Navigation -->
    <nav 
      ref="navContainer" 
      :class="[
        'scrollbar-thin space-y-0 overflow-y-auto overflow-x-hidden',
        maxHeight || 'max-h-[calc(100vh-8rem)]'
      ]"
    >
      <slot name="content" :nav-container="navContainer" />
    </nav>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useLookupMode } from '@/stores/search/modes/lookup';

interface Props {
  maxHeight?: string;
}

defineProps<Props>();

const lookupMode = useLookupMode();
const selectedCardVariant = computed(() => lookupMode.selectedCardVariant);

// Template refs - exposed to content slot
const navContainer = ref<HTMLElement>();

// Expose for composables that need scroll control
defineExpose({
  navContainer
});
</script>