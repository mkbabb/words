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
        class="fixed inset-0 flex items-center justify-center"
        style="z-index: 99999"
        @click="handleBackdropClick"
      >
        <!-- Backdrop -->
        <div
          ref="backdropRef"
          class="absolute inset-0 bg-background/60 dark:bg-background/70 backdrop-blur-2xl"
        />

        <!-- Close button -->
        <button
          class="absolute top-4 right-4 z-20 flex h-8 w-8 items-center justify-center rounded-full border border-border/30 bg-background/60 text-muted-foreground backdrop-blur-sm transition-colors hover:bg-background/80 hover:text-foreground"
          @click.stop="handleClose"
        >
          <X :size="16" />
        </button>

        <!-- Content card -->
        <div
          ref="contentRef"
          class="relative z-10 max-w-3xl w-full mx-4 rounded-2xl border border-border/30 bg-background/80 shadow-2xl backdrop-blur-xl p-8"
          @click.stop
        >
          <!-- Header -->
          <div class="flex items-center gap-2 mb-6">
            <h2 class="text-lg font-semibold tracking-tight">
              Review: {{ wordlistName }}
            </h2>
            <Badge v-if="dueWords.length > 0" variant="secondary" class="text-xs">
              {{ currentIndex + 1 }}/{{ dueWords.length }}
            </Badge>
          </div>

          <!-- Loading State -->
          <div v-if="isLoading" class="flex flex-col items-center justify-center py-12 gap-3">
            <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p class="text-sm text-muted-foreground">Loading review session...</p>
          </div>

          <!-- Empty State -->
          <div v-else-if="dueWords.length === 0 && !sessionComplete" class="flex flex-col items-center justify-center py-12 gap-3">
            <img :src="yoshiYellowStanding" alt="" class="h-12 w-12" />
            <p class="text-lg font-medium">No words due for review</p>
            <p class="text-sm text-muted-foreground">Check back later or add more words.</p>
            <Button variant="outline" @click="handleClose">Close</Button>
          </div>

          <!-- Session Complete -->
          <div v-else-if="sessionComplete" class="flex flex-col items-center gap-4 py-6">
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

            <Button class="mt-2" @click="handleSessionClose">Done</Button>
          </div>

          <!-- Review Card -->
          <div v-else class="space-y-4">
            <!-- Progress -->
            <div class="h-2 w-full overflow-hidden rounded-full bg-muted/50">
              <div
                class="h-full rounded-full transition-all duration-500 ease-apple-smooth"
                :style="{
                  width: `${progressPercent}%`,
                  background: 'linear-gradient(to right, var(--review-again), var(--review-good), var(--review-easy))',
                  boxShadow: '0 0 8px color-mix(in srgb, var(--review-good) 40%, transparent)',
                }"
              />
            </div>

            <!-- Word Card -->
            <ThemedCard
              :variant="currentWord.mastery_level"
              class="relative p-6"
              :border-shimmer="true"
            >
              <!-- State Badge -->
              <div class="flex items-center gap-2 mb-3">
                <span
                  :class="['inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', currentStateBadgeClasses]"
                >
                  {{ currentStateLabel }}
                </span>
                <Badge v-if="currentWord.is_leech" variant="destructive" class="text-xs">
                  Leech
                </Badge>
              </div>

              <!-- Word -->
              <p class="text-2xl font-serif font-bold text-center py-4">
                {{ currentWord.word }}
              </p>

              <!-- Notes -->
              <p v-if="currentWord.notes" class="text-xs text-muted-foreground text-center italic mb-2">
                {{ currentWord.notes }}
              </p>

              <!-- Reveal Button -->
              <div v-if="!isRevealed" class="flex justify-center">
                <Button
                  :disabled="isLookingUp"
                  @click="handleReveal"
                >
                  <span v-if="isLookingUp" class="flex items-center gap-2">
                    <span class="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                    Looking up...
                  </span>
                  <span v-else>Reveal</span>
                </Button>
              </div>

              <!-- Definition Preview -->
              <div v-if="isRevealed && revealedDefinition" class="mt-4 space-y-2 text-sm border-t pt-3">
                <div>
                  <ul class="list-disc list-inside space-y-1">
                    <li
                      v-for="(def, j) in revealedDefinition.definitions?.slice(0, 4)"
                      :key="j"
                      class="text-foreground/90"
                    >
                      {{ def.text }}
                    </li>
                  </ul>
                </div>
              </div>

              <!-- Lookup Timed Out -->
              <div
                v-if="isRevealed && lookupTimedOut"
                class="mt-4 text-sm text-center cursor-pointer text-amber-500 hover:text-amber-400 transition-colors"
                @click="handleReveal"
              >
                Lookup timed out — tap to retry
              </div>

              <!-- Lookup Error (non-timeout) -->
              <p v-else-if="isRevealed && lookupError" class="mt-4 text-sm text-destructive text-center">
                {{ lookupError }}
              </p>
            </ThemedCard>

            <!-- Quality Buttons -->
            <div v-if="isRevealed" class="space-y-2">
              <p class="text-xs text-muted-foreground text-center">How well did you recall this word?</p>
              <div class="flex justify-center gap-2">
                <template v-for="btn in qualityButtons" :key="btn.quality">
                  <button
                    :disabled="isSubmitting"
                    :class="[
                      'flex flex-col items-center gap-0.5 h-auto py-3 px-5 min-w-[7rem] rounded-xl text-sm font-medium transition-fast',
                      'hover:scale-[1.03] active:scale-[0.97]',
                      'disabled:opacity-50 disabled:pointer-events-none',
                      btn.buttonClass,
                    ]"
                    @click="handleQualitySubmit(btn.quality)"
                  >
                    <span class="flex items-center gap-1.5 text-sm font-medium">
                      <component :is="btn.icon" :size="16" />
                      {{ btn.label }}
                    </span>
                    <span class="text-[10px] opacity-70">{{ formatInterval(btn.interval) }}</span>
                  </button>
                </template>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onUnmounted, type Component } from 'vue';
import { X, AlertTriangle, Check, Zap } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ThemedCard } from '@/components/custom/card';
import yoshiGreenStanding from '@/assets/yoshi/standing/yoshi_green_standing.png';
import yoshiYellowStanding from '@/assets/yoshi/standing/yoshi_yellow_standing.png';
import { wordlistApi, lookupApi } from '@/api';
import type { DueWordItem, ReviewResult, SM2Quality } from '@/types/wordlist';
import type { SynthesizedDictionaryEntry } from '@/types';
import {
  formatInterval,
  getCardStateLabelFull,
  getCardStateBadgeClasses,
  getReviewButtonClass,
} from '../utils/formatting';

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
const isLookingUp = ref(false);
const isSubmitting = ref(false);
const lookupError = ref<string | null>(null);
const lookupTimedOut = ref(false);
const revealedDefinition = ref<SynthesizedDictionaryEntry | null>(null);

// Current word
const currentWord = computed<DueWordItem>(() => dueWords.value[currentIndex.value]);

// Progress
const progressPercent = computed(() => {
  if (dueWords.value.length === 0) return 0;
  return Math.round((currentIndex.value / dueWords.value.length) * 100);
});

// Mastery promotions count
const masteryPromotions = computed(() =>
  results.value.filter((r) => r.result.mastery_changed).length
);

// Card state display using shared utils
const currentStateLabel = computed(() =>
  getCardStateLabelFull(currentWord.value?.card_state)
);

const currentStateBadgeClasses = computed(() =>
  getCardStateBadgeClasses(currentWord.value?.card_state)
);

// Quality buttons based on card state
const qualityButtons = computed(() => {
  const word = currentWord.value;
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

// Escape key handler
function handleEscape(event: KeyboardEvent) {
  if (event.key === 'Escape') handleClose();
}

// Body scroll lock + escape listener
watch(
  () => props.modelValue,
  (open) => {
    document.body.style.overflow = open ? 'hidden' : '';
    if (open) {
      document.addEventListener('keydown', handleEscape);
    } else {
      document.removeEventListener('keydown', handleEscape);
    }
  }
);

onUnmounted(() => {
  document.body.style.overflow = '';
  document.removeEventListener('keydown', handleEscape);
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
  isLookingUp.value = false;
  isSubmitting.value = false;
  lookupError.value = null;
  lookupTimedOut.value = false;
  revealedDefinition.value = null;
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

    // Advance to next word or complete
    if (currentIndex.value + 1 < dueWords.value.length) {
      currentIndex.value++;
      isRevealed.value = false;
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

function overlayLeave(el: Element, done: () => void) {
  const backdrop = el.querySelector('[class*="backdrop-blur"]') as HTMLElement;
  const content = contentRef.value;

  if (!backdrop) { done(); return; }

  requestAnimationFrame(() => {
    if (content) {
      content.style.transition = 'opacity 150ms cubic-bezier(0.4, 0, 0.2, 1), transform 150ms cubic-bezier(0.4, 0, 0.2, 1)';
      content.style.opacity = '0';
      content.style.transform = 'scale(0.97) translateY(8px)';
    }
    backdrop.style.transition = 'opacity 180ms cubic-bezier(0.4, 0, 0.2, 1)';
    backdrop.style.opacity = '0';

    setTimeout(done, 200);
  });
}
</script>
