<template>
  <div class="mt-3.5 space-y-1">
    <div class="h-1.5 w-full overflow-hidden rounded-full bg-muted/60 flex">
      <!-- Mastered (gold) -->
      <div
        class="h-full"
        :style="{
          width: barWidth('mastered') + '%',
          background: 'linear-gradient(90deg, var(--mastery-gold), color-mix(in srgb, var(--mastery-gold) 85%, black))',
        }"
      />
      <!-- Familiar (silver) -->
      <div
        class="h-full"
        :style="{
          width: barWidth('familiar') + '%',
          background: 'linear-gradient(90deg, var(--mastery-silver), color-mix(in srgb, var(--mastery-silver) 85%, black))',
        }"
      />
      <!-- Learning (bronze) -->
      <div
        class="h-full"
        :style="{
          width: barWidth('learning') + '%',
          background: 'linear-gradient(90deg, var(--mastery-bronze), color-mix(in srgb, var(--mastery-bronze) 85%, black))',
        }"
      />
    </div>
    <!-- Legend pills (only if there's any data) -->
    <div
      v-if="hasData"
      class="flex items-center gap-2 text-[10px] text-muted-foreground/50"
    >
      <span v-if="masteredCount > 0" class="flex items-center gap-1">
        <span class="inline-block h-1.5 w-1.5 rounded-full" style="background: var(--mastery-gold)" />
        {{ masteredCount }} mastered
      </span>
      <span v-if="learningCount > 0" class="flex items-center gap-1">
        <span class="inline-block h-1.5 w-1.5 rounded-full" style="background: var(--mastery-bronze)" />
        {{ learningCount }} learning
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
  masteredCount: number;
  familiarCount: number;
  learningCount: number;
  totalWords: number;
}

const props = defineProps<Props>();

const hasData = computed(() => props.totalWords > 0);

function barWidth(bucket: 'mastered' | 'familiar' | 'learning'): number {
  if (!props.totalWords) return 0;
  const count = bucket === 'mastered' ? props.masteredCount
    : bucket === 'familiar' ? props.familiarCount
    : props.learningCount;
  return (count / props.totalWords) * 100;
}
</script>
