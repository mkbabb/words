<template>
  <div class="flex flex-col items-center gap-4 py-6">
    <!-- CSS-only confetti on gold promotion -->
    <template v-if="hasGoldPromotion">
      <div
        v-for="i in 20"
        :key="'confetti-' + i"
        class="confetti-piece"
        :style="{
          left: `${Math.random() * 100}%`,
          backgroundColor: confettiColors[i % confettiColors.length],
          animationDelay: `${Math.random() * 0.5}s`,
          animationDuration: `${1.5 + Math.random()}s`,
        }"
      />
    </template>

    <img :src="yoshiGreenStanding" alt="" class="h-16 w-16 mx-auto mb-2" />
    <p class="text-xl font-semibold">Session Complete</p>

    <div class="grid grid-cols-2 gap-4 w-full max-w-xs text-center">
      <div class="stat-mastery">
        <p class="text-2xl font-bold text-primary">{{ results.length }}</p>
        <p class="text-xs text-muted-foreground">Cards Reviewed</p>
      </div>
      <div class="stat-mastery border-mastery-gold bg-mastery-gold">
        <p class="text-2xl font-bold mastery-gold">{{ masteryPromotions }}</p>
        <p class="text-xs text-muted-foreground">Mastery Promotions</p>
      </div>
    </div>

    <!-- Mastery Transitions -->
    <div v-if="masteryTransitions.length > 0" class="w-full max-w-xs space-y-1 mt-2">
      <p class="text-sm font-medium text-center">Mastery Promotions</p>
      <div
        v-for="t in masteryTransitions"
        :key="t.word"
        class="flex items-center justify-between gap-2 text-xs px-2 py-1 rounded bg-muted/50"
      >
        <span class="font-medium truncate">{{ t.word }}</span>
        <span class="text-muted-foreground flex-shrink-0">{{ t.from }} &rarr; {{ t.to }}</span>
      </div>
    </div>

    <!-- Next Session Preview -->
    <div v-if="results.length > 0" class="w-full max-w-xs space-y-1 mt-2 text-center">
      <p class="text-sm font-medium">Upcoming Reviews</p>
      <div class="flex justify-center gap-6 text-xs text-muted-foreground">
        <div>
          <p class="text-lg font-bold text-foreground">{{ dueTomorrow }}</p>
          <p>Tomorrow</p>
        </div>
        <div>
          <p class="text-lg font-bold text-foreground">{{ dueIn4Days }}</p>
          <p>In 4 days</p>
        </div>
      </div>
    </div>

    <Button class="mt-2" @click="$emit('done')">Done</Button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Button } from '@mkbabb/glass-ui';
import yoshiGreenStanding from '@/assets/yoshi/standing/yoshi_green_standing.png';
import type { ReviewResult, SM2Quality } from '@/types/wordlist';

interface ReviewResultEntry {
  word: string;
  quality: SM2Quality;
  result: ReviewResult;
}

interface MasteryTransition {
  word: string;
  from: string;
  to: string;
}

interface Props {
  results: ReviewResultEntry[];
  masteryTransitions: MasteryTransition[];
}

interface Emits {
  (e: 'done'): void;
}

const props = defineProps<Props>();
defineEmits<Emits>();

// Confetti colors
const confettiColors = ['#fbbf24', '#f59e0b', '#ef4444', '#3b82f6', '#10b981', '#8b5cf6', '#ec4899'];

// Mastery promotions count
const masteryPromotions = computed(() =>
  props.results.filter((r) => r.result.mastery_changed).length
);

const hasGoldPromotion = computed(() =>
  props.masteryTransitions.some(t => t.to === 'gold')
);

const dueTomorrow = computed(() => {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  tomorrow.setHours(23, 59, 59, 999);
  return props.results.filter(r => {
    const next = new Date(r.result.next_review_date);
    return next <= tomorrow;
  }).length;
});

const dueIn4Days = computed(() => {
  const future = new Date();
  future.setDate(future.getDate() + 4);
  future.setHours(23, 59, 59, 999);
  return props.results.filter(r => {
    const next = new Date(r.result.next_review_date);
    return next <= future;
  }).length;
});
</script>
