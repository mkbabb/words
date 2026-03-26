<template>
  <Teleport to="body">
    <Transition
      :css="false"
      @before-enter="beforeEnter"
      @enter="overlayEnter"
      @leave="overlayLeave"
    >
      <div
        v-if="modelValue"
        class="fixed inset-0 z-modal flex items-center justify-center"
        style="isolation: isolate"
        @click="handleBackdropClick"
      >
        <!-- Backdrop — fully opaque to prevent bleed-through -->
        <div
          ref="backdropRef"
          class="dialog-overlay absolute inset-0"
        />

        <!-- Close button -->
        <button
          class="absolute top-4 right-4 z-20 flex h-8 w-8 items-center justify-center rounded-full glass-light text-foreground/70 transition-colors hover:bg-background/90 hover:text-foreground"
          @click.stop="handleClose"
        >
          <X :size="16" />
        </button>

        <!-- Content card -->
        <div
          ref="contentRef"
          class="dialog-surface relative z-10 mx-4 max-h-[90svh] w-full max-w-3xl overflow-y-auto p-8 scrollbar-thin"
          :style="{ backgroundImage: 'var(--paper-clean-texture)', backgroundBlendMode: 'multiply' }"
          @click.stop
        >
          <!-- Header -->
          <div class="flex items-center gap-3 mb-6">
            <div class="flex-1 min-w-0">
              <h2 class="text-heading tracking-tight truncate">
                {{ wordlistName }}
              </h2>
              <p class="text-sm text-muted-foreground mt-0.5">
                {{ dueWords.length }} {{ dueWords.length === 1 ? 'card' : 'cards' }} to review
                <template v-if="results.length > 0"> &middot; {{ results.length }} done</template>
              </p>
            </div>
            <!-- Progress Ring -->
            <div v-if="dueWords.length > 0" class="relative flex-shrink-0">
              <svg class="w-12 h-12" viewBox="0 0 48 48">
                <circle cx="24" cy="24" r="20" fill="none" stroke="currentColor" stroke-width="3" class="text-muted opacity-20" />
                <circle cx="24" cy="24" r="20" fill="none" stroke="currentColor" stroke-width="3" class="text-primary"
                  :stroke-dasharray="`${2 * Math.PI * 20}`"
                  :stroke-dashoffset="`${2 * Math.PI * 20 * (1 - progressRatio)}`"
                  stroke-linecap="round"
                  transform="rotate(-90 24 24)"
                  style="transition: stroke-dashoffset 0.5s ease"
                />
              </svg>
              <span class="absolute inset-0 flex items-center justify-center text-xs font-medium">
                {{ currentIndex + 1 }}/{{ dueWords.length }}
              </span>
            </div>
          </div>

          <!-- Loading State -->
          <div v-if="isLoading" class="flex flex-col items-center justify-center py-12 gap-3">
            <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p class="text-sm text-muted-foreground">Loading review session...</p>
          </div>

          <!-- Empty State -->
          <div v-else-if="dueWords.length === 0 && !sessionComplete" class="flex flex-col items-center justify-center py-12 gap-3">
            <img :src="yoshiYellowStanding" alt="" class="h-12 w-12" />
            <p class="text-subheading">No words due for review</p>
            <p class="text-sm text-muted-foreground">Check back later or add more words.</p>
            <Button variant="outline" @click="handleClose">Close</Button>
          </div>

          <!-- Session Complete -->
          <ReviewSessionComplete
            v-else-if="sessionComplete"
            :results="results"
            :mastery-transitions="masteryTransitions"
            @done="handleSessionClose"
          />

          <!-- Review Card + Quality Buttons -->
          <template v-else>
            <ReviewCard
              :current-word="currentWord"
              :is-flipped="isFlipped"
              :is-looking-up="isLookingUp"
              :revealed-definition="revealedDefinition"
              :lookup-timed-out="lookupTimedOut"
              :lookup-error="lookupError"
              :is-revealed="isRevealed"
              :state-label="currentStateLabel"
              :state-badge-classes="currentStateBadgeClasses"
              :progress-ratio="progressRatio"
              @reveal="handleReveal"
              @swipe-quality="handleQualitySubmit"
            />

            <!-- Quality Buttons -->
            <ReviewQualityButtons
              :is-revealed="isRevealed"
              :is-submitting="isSubmitting"
              :current-word="currentWord"
              @submit="handleQualitySubmit"
            />
          </template>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from 'vue';
import { X } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import yoshiYellowStanding from '@/assets/yoshi/standing/yoshi_yellow_standing.png';
import { wordlistApi, lookupApi } from '@/api';
import type { DueWordItem, ReviewResult, SM2Quality } from '@/types/wordlist';
import type { SynthesizedDictionaryEntry } from '@/types';
import {
  getCardStateLabelFull,
  getCardStateBadgeClasses,
} from '../utils/formatting';
import ReviewCard from './ReviewCard.vue';
import ReviewQualityButtons from './ReviewQualityButtons.vue';
import ReviewSessionComplete from './ReviewSessionComplete.vue';

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

// Animation refs
const backdropRef = ref<HTMLDivElement>();
const contentRef = ref<HTMLDivElement>();

// Session state
const dueWords = ref<DueWordItem[]>([]);
const currentIndex = ref(0);
const results = ref<{ word: string; quality: SM2Quality; result: ReviewResult }[]>([]);
const sessionComplete = ref(false);

// UI state
const isLoading = ref(false);
const isRevealed = ref(false);
const isFlipped = ref(false);
const isLookingUp = ref(false);
const isSubmitting = ref(false);
const lookupError = ref<string | null>(null);
const lookupTimedOut = ref(false);
const revealedDefinition = ref<SynthesizedDictionaryEntry | null>(null);

// Mastery transitions tracking
const masteryTransitions = ref<Array<{ word: string; from: string; to: string }>>([]);

// Current word
const currentWord = computed<DueWordItem>(() => dueWords.value[currentIndex.value]);

// Progress
const progressRatio = computed(() => {
  if (dueWords.value.length === 0) return 0;
  return currentIndex.value / dueWords.value.length;
});

// Card state display using shared utils
const currentStateLabel = computed(() =>
  getCardStateLabelFull(currentWord.value?.card_state)
);

const currentStateBadgeClasses = computed(() =>
  getCardStateBadgeClasses(currentWord.value?.card_state)
);

// Keyboard shortcuts handler
function handleKeyboard(event: KeyboardEvent) {
  if (sessionComplete.value || isLoading.value || dueWords.value.length === 0) return;

  if (event.key === ' ' && !isRevealed.value && !isLookingUp.value) {
    event.preventDefault();
    handleReveal();
    return;
  }

  if (!isRevealed.value || isSubmitting.value) return;

  const keyMap: Record<string, SM2Quality> = { '1': 0, '2': 2, '3': 4, '4': 5 };
  const quality = keyMap[event.key];
  if (quality !== undefined) {
    event.preventDefault();
    handleQualitySubmit(quality);
  }
}

// Escape key handler
function handleEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') handleClose();
}

// Body scroll lock + escape + keyboard listener
watch(
  () => props.modelValue,
  (open) => {
    const lockVal = open ? 'hidden' : '';
    document.body.style.overflow = lockVal;
    document.documentElement.style.overflow = lockVal;
    if (open) {
      document.addEventListener('keydown', handleEscape);
      document.addEventListener('keydown', handleKeyboard);
    } else {
      document.removeEventListener('keydown', handleEscape);
      document.removeEventListener('keydown', handleKeyboard);
    }
  }
);

onUnmounted(() => {
  document.body.style.overflow = '';
  document.documentElement.style.overflow = '';
  document.removeEventListener('keydown', handleEscape);
  document.removeEventListener('keydown', handleKeyboard);
});

// Fetch session on open
watch(
  () => props.modelValue,
  async (isOpen) => {
    if (isOpen) {
      await fetchSession();
    } else {
      resetState();
    }
  }
);

async function fetchSession() {
  isLoading.value = true;
  try {
    const response = await wordlistApi.getReviewSession(props.wordlistId);
    // FIX: API returns { data: { words: [...] } } — unwrap correctly
    const data = response.data ?? response;
    dueWords.value = data.words ?? [];

    // Filter to selected words when provided
    if (props.selectedWords?.length) {
      const selected = new Set(props.selectedWords);
      dueWords.value = dueWords.value.filter(w => selected.has(w.word));
    }

    currentIndex.value = 0;
    results.value = [];
    sessionComplete.value = false;
    isRevealed.value = false;
  } catch (err: any) {
    dueWords.value = [];
  } finally {
    isLoading.value = false;
  }
}

function resetState() {
  dueWords.value = [];
  currentIndex.value = 0;
  results.value = [];
  sessionComplete.value = false;
  isRevealed.value = false;
  isFlipped.value = false;
  isLookingUp.value = false;
  isSubmitting.value = false;
  lookupError.value = null;
  lookupTimedOut.value = false;
  revealedDefinition.value = null;
  masteryTransitions.value = [];
}

async function handleReveal() {
  isLookingUp.value = true;
  lookupError.value = null;
  lookupTimedOut.value = false;
  revealedDefinition.value = null;

  try {
    const entry = await lookupApi.lookup(currentWord.value.word, { timeout: 15000 });
    revealedDefinition.value = entry;
  } catch (err: any) {
    // Detect timeout: axios uses code 'ECONNABORTED' for timeouts
    if (err?.code === 'ECONNABORTED' || err?.message?.toLowerCase().includes('timeout')) {
      lookupTimedOut.value = true;
    } else {
      lookupError.value = err?.message ?? 'Failed to look up definition';
    }
  } finally {
    isLookingUp.value = false;
    isRevealed.value = true;
    isFlipped.value = true;
  }
}

async function handleQualitySubmit(quality: SM2Quality) {
  isSubmitting.value = true;
  try {
    // FIX: API returns { data: {...} } — unwrap correctly
    const response = await wordlistApi.submitWordReview(props.wordlistId, {
      word: currentWord.value.word,
      quality,
    });
    const result: ReviewResult = response.data ?? response;

    results.value.push({
      word: currentWord.value.word,
      quality,
      result,
    });

    // Track mastery transitions
    if (result.mastery_changed && result.previous_mastery) {
      masteryTransitions.value.push({
        word: currentWord.value.word,
        from: result.previous_mastery,
        to: result.mastery_level,
      });
    }

    // Advance to next word or complete
    if (currentIndex.value + 1 < dueWords.value.length) {
      currentIndex.value++;
      isRevealed.value = false;
      isFlipped.value = false;
      isLookingUp.value = false;
      lookupError.value = null;
      lookupTimedOut.value = false;
      revealedDefinition.value = null;
    } else {
      sessionComplete.value = true;
    }
  } catch (err: any) {
    // On error, still allow retrying
  } finally {
    isSubmitting.value = false;
  }
}

function handleClose() {
  emit('update:modelValue', false);
}

function handleSessionClose() {
  emit('session-complete');
  emit('update:modelValue', false);
}

function handleBackdropClick(event: Event) {
  const target = event.target as Element;
  if (target === event.currentTarget || target === backdropRef.value) {
    handleClose();
  }
}

// JS-driven transitions matching TimeMachineOverlay pattern
function beforeEnter() {
  if (backdropRef.value) {
    backdropRef.value.style.transition = 'none';
    backdropRef.value.style.opacity = '0';
  }
  if (contentRef.value) {
    contentRef.value.style.transition = 'none';
    contentRef.value.style.opacity = '0';
    contentRef.value.style.transform = 'scale(0.92) translateY(20px)';
  }
}

function overlayEnter(_el: Element, done: () => void) {
  if (!backdropRef.value || !contentRef.value) {
    done();
    return;
  }

  void backdropRef.value.offsetHeight;

  requestAnimationFrame(() => {
    if (!backdropRef.value || !contentRef.value) {
      done();
      return;
    }

    // Backdrop fade — fast
    backdropRef.value.style.transition = 'opacity 200ms cubic-bezier(0.4, 0, 0.2, 1)';
    backdropRef.value.style.opacity = '1';

    // Content slide up — slightly staggered
    setTimeout(() => {
      if (!contentRef.value) { done(); return; }
      contentRef.value.style.transition = 'opacity 250ms cubic-bezier(0.4, 0, 0.2, 1), transform 250ms cubic-bezier(0.4, 0, 0.2, 1)';
      contentRef.value.style.opacity = '1';
      contentRef.value.style.transform = 'scale(1) translateY(0)';

      setTimeout(done, 300);
    }, 30);
  });
}

function overlayLeave(_el: Element, done: () => void) {
  const backdrop = backdropRef.value;
  const content = contentRef.value;

  if (!backdrop && !content) { done(); return; }

  requestAnimationFrame(() => {
    if (content) {
      content.style.transition = 'opacity 150ms cubic-bezier(0.4, 0, 0.2, 1), transform 150ms cubic-bezier(0.4, 0, 0.2, 1)';
      content.style.opacity = '0';
      content.style.transform = 'scale(0.97) translateY(8px)';
    }
    if (backdrop) {
      backdrop.style.transition = 'opacity 180ms cubic-bezier(0.4, 0, 0.2, 1)';
      backdrop.style.opacity = '0';
    }

    setTimeout(done, 200);
  });
}
</script>

<style>
/* Rainbow shimmer for loading indicator */
.rainbow-shimmer {
  background: linear-gradient(90deg, #ef4444, #f59e0b, #22c55e, #3b82f6, #8b5cf6, #ef4444);
  background-size: 200% 100%;
  animation: rainbow-slide 1.5s linear infinite;
}

@keyframes rainbow-slide {
  0% { background-position: 0% 0; }
  100% { background-position: 200% 0; }
}

/* Card face crossfade transition */
.card-fade-enter-active {
  transition: opacity 0.25s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}
.card-fade-leave-active {
  transition: opacity 0.15s cubic-bezier(0.4, 0, 0.2, 1),
              transform 0.15s cubic-bezier(0.4, 0, 0.2, 1);
}
.card-fade-enter-from {
  opacity: 0;
  transform: translateY(-4px);
}
.card-fade-leave-to {
  opacity: 0;
  transform: translateY(4px);
}

/* CSS-only confetti */
@keyframes confetti-fall {
  0% { transform: translateY(-100%) rotate(0deg); opacity: 1; }
  100% { transform: translateY(100vh) rotate(720deg); opacity: 0; }
}

.confetti-piece {
  position: fixed;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  z-index: 55;
  pointer-events: none;
  animation: confetti-fall 2s ease-in forwards;
}
</style>
