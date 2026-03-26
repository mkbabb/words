<template>
  <div v-if="isRevealed" class="space-y-3">
    <p class="text-xs text-muted-foreground text-center">How well did you recall this word?</p>
    <div class="flex justify-center gap-2.5">
      <template v-for="(btn, btnIdx) in qualityButtons" :key="btn.quality">
        <button
          :disabled="isSubmitting"
          :class="[
            'flex flex-col items-center gap-1 h-auto py-3 px-5 min-w-[7rem] rounded-2xl text-sm font-semibold transition-fast',
            'hover:-translate-y-0.5 hover:shadow-lg active:scale-[0.96]',
            'disabled:opacity-50 disabled:pointer-events-none',
            btn.buttonClass,
          ]"
          @click="$emit('submit', btn.quality)"
        >
          <span class="flex items-center gap-1.5 text-sm font-semibold">
            <component :is="btn.icon" :size="18" />
            {{ btn.label }}
          </span>
          <span class="text-micro opacity-60 tabular-nums">{{ formatInterval(btn.interval) }}</span>
          <kbd class="text-micro opacity-40 border border-current/20 rounded px-1 mt-0.5">{{ btnIdx + 1 }}</kbd>
        </button>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Component } from 'vue';
import { computed } from 'vue';
import { X, AlertTriangle, Check, Zap } from 'lucide-vue-next';
import type { DueWordItem, SM2Quality } from '@/types/wordlist';
import {
  formatInterval,
  getReviewButtonClass,
} from '../utils/formatting';

interface Props {
  isRevealed: boolean;
  isSubmitting: boolean;
  currentWord: DueWordItem;
}

interface Emits {
  (e: 'submit', quality: SM2Quality): void;
}

const props = defineProps<Props>();
defineEmits<Emits>();

// Quality buttons based on card state
const qualityButtons = computed(() => {
  const word = props.currentWord;
  if (!word) return [];

  const intervals = word.predicted_intervals ?? {};
  const state = word.card_state;

  // Learning/Relearning: Again(0), Good(3), Easy(5)
  if (state === 'learning' || state === 'relearning' || state === 'new') {
    return [
      { quality: 0 as SM2Quality, label: 'Forgot', icon: X as Component, buttonClass: getReviewButtonClass(0), interval: intervals[0] },
      { quality: 3 as SM2Quality, label: 'Remembered', icon: Check as Component, buttonClass: getReviewButtonClass(3), interval: intervals[3] },
      { quality: 5 as SM2Quality, label: 'Effortless', icon: Zap as Component, buttonClass: getReviewButtonClass(5), interval: intervals[5] },
    ];
  }

  // Young/Mature: Again(0), Hard(2), Good(4), Easy(5)
  return [
    { quality: 0 as SM2Quality, label: 'Forgot', icon: X as Component, buttonClass: getReviewButtonClass(0), interval: intervals[0] },
    { quality: 2 as SM2Quality, label: 'Struggled', icon: AlertTriangle as Component, buttonClass: getReviewButtonClass(2), interval: intervals[2] },
    { quality: 4 as SM2Quality, label: 'Remembered', icon: Check as Component, buttonClass: getReviewButtonClass(4), interval: intervals[4] },
    { quality: 5 as SM2Quality, label: 'Effortless', icon: Zap as Component, buttonClass: getReviewButtonClass(5), interval: intervals[5] },
  ];
});
</script>
