<template>
  <div class="inline-flex items-center gap-1.5 text-xs text-muted-foreground/50 px-2 py-0.5 border border-border/30 rounded-md bg-background/50">
    <span v-if="version">v{{ version }}</span>
    <span v-if="lastUpdated" class="text-muted-foreground/40">
      {{ formattedDate }}
    </span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface VersionBadgeProps {
  version?: number | string;
  lastUpdated?: string;
}

const props = defineProps<VersionBadgeProps>();

const formattedDate = computed(() => {
  if (!props.lastUpdated) return '';
  try {
    const date = new Date(props.lastUpdated);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  } catch {
    return props.lastUpdated;
  }
});
</script>
