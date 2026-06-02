<template>
  <Modal v-model="modelValue" max-width="3xl" max-height="viewport">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-6">
      <div class="flex-1 min-w-0">
        <h2 class="text-subheading tracking-tight truncate">
          {{ wordlistName }}
        </h2>
        <p class="text-sm text-muted-foreground mt-0.5">
          {{ session.dueWords.value.length }} {{ session.dueWords.value.length === 1 ? 'card' : 'cards' }} to review
          <template v-if="session.results.value.length > 0"> &middot; {{ session.results.value.length }} done</template>
        </p>
      </div>
      <!-- Progress Ring -->
      <div v-if="session.dueWords.value.length > 0" class="relative flex-shrink-0">
        <svg class="w-12 h-12" viewBox="0 0 48 48">
          <circle cx="24" cy="24" r="20" fill="none" stroke="currentColor" stroke-width="3" class="text-muted opacity-20" />
          <circle cx="24" cy="24" r="20" fill="none" stroke="currentColor" stroke-width="3" class="text-primary"
            :stroke-dasharray="`${2 * Math.PI * 20}`"
            :stroke-dashoffset="`${2 * Math.PI * 20 * (1 - session.progressRatio.value)}`"
            stroke-linecap="round"
            transform="rotate(-90 24 24)"
            style="transition: stroke-dashoffset 0.5s ease"
          />
        </svg>
        <span class="absolute inset-0 flex items-center justify-center text-xs font-medium">
          {{ session.currentIndex.value + 1 }}/{{ session.dueWords.value.length }}
        </span>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="session.isLoading.value" class="flex flex-col items-center justify-center py-12 gap-3">
      <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      <p class="text-sm text-muted-foreground">Loading review session...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="session.dueWords.value.length === 0 && !session.sessionComplete.value" class="flex flex-col items-center justify-center py-12 gap-3">
      <img :src="yoshiYellowStanding" alt="" class="h-12 w-12" />
      <p class="text-subheading">No words due for review</p>
      <p class="text-sm text-muted-foreground">Check back later or add more words.</p>
      <Button variant="outline" @click="session.handleClose">Close</Button>
    </div>

    <!-- Session Complete -->
    <ReviewSessionComplete
      v-else-if="session.sessionComplete.value"
      :results="session.results.value"
      :mastery-transitions="session.masteryTransitions.value"
      @done="session.handleSessionClose"
    />

    <!-- Review Card + Quality Buttons -->
    <template v-else>
      <ReviewCard
        :current-word="session.currentWord.value"
        :is-flipped="session.isFlipped.value"
        :is-looking-up="session.isLookingUp.value"
        :revealed-definition="session.revealedDefinition.value"
        :lookup-timed-out="session.lookupTimedOut.value"
        :lookup-error="session.lookupError.value"
        :is-revealed="session.isRevealed.value"
        :state-label="session.currentStateLabel.value"
        :state-badge-classes="session.currentStateBadgeClasses.value"
        :progress-ratio="session.progressRatio.value"
        @reveal="session.handleReveal"
        @swipe-quality="session.handleQualitySubmit"
      />

      <!-- Quality Buttons -->
      <ReviewQualityButtons
        :is-revealed="session.isRevealed.value"
        :is-submitting="session.isSubmitting.value"
        :current-word="session.currentWord.value"
        @submit="session.handleQualitySubmit"
      />
    </template>
  </Modal>
</template>

<script setup lang="ts">
import { computed, toRef } from 'vue';
import { Button } from '@mkbabb/glass-ui/button';
import yoshiYellowStanding from '@/assets/yoshi/standing/yoshi_yellow_standing.png';
import Modal from '@/components/custom/Modal.vue';
import ReviewCard from './ReviewCard.vue';
import ReviewQualityButtons from './ReviewQualityButtons.vue';
import ReviewSessionComplete from './ReviewSessionComplete.vue';
import { useReviewSession } from './composables/useReviewSession';

interface Props {
  modelValue: boolean;
  wordlistId: string;
  wordlistName: string;
  selectedWords?: string[];
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void;
  (e: 'session-complete'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const modelValue = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
});

const session = useReviewSession({
  wordlistId: toRef(props, 'wordlistId'),
  selectedWords: toRef(props, 'selectedWords'),
  modelValue: toRef(props, 'modelValue'),
  onClose: () => emit('update:modelValue', false),
  onSessionClose: () => {
    emit('session-complete');
    emit('update:modelValue', false);
  },
});
</script>
