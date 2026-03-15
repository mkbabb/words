<template>
  <Dialog
    :open="modelValue"
    @update:open="$emit('update:modelValue', $event)"
  >
    <DialogContent
      class="sm:max-w-lg bg-background/80 backdrop-blur-xl border-border/50"
      @pointer-down-outside.prevent
    >
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          Review: {{ wordlistName }}
          <Badge v-if="dueWords.length > 0" variant="secondary" class="text-xs">
            {{ currentIndex + 1 }}/{{ dueWords.length }}
          </Badge>
        </DialogTitle>
      </DialogHeader>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex flex-col items-center justify-center py-12 gap-3">
        <div class="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <p class="text-sm text-muted-foreground">Loading review session...</p>
      </div>

      <!-- Empty State -->
      <div v-else-if="dueWords.length === 0 && !sessionComplete" class="flex flex-col items-center justify-center py-12 gap-3">
        <p class="text-lg font-medium">No words due for review</p>
        <p class="text-sm text-muted-foreground">Check back later or add more words.</p>
        <Button variant="outline" @click="$emit('update:modelValue', false)">Close</Button>
      </div>

      <!-- Session Complete -->
      <div v-else-if="sessionComplete" class="flex flex-col items-center gap-4 py-6">
        <p class="text-xl font-semibold">Session Complete</p>

        <div class="grid grid-cols-2 gap-4 w-full max-w-xs text-center">
          <div class="rounded-lg border p-3">
            <p class="text-2xl font-bold text-primary">{{ results.length }}</p>
            <p class="text-xs text-muted-foreground">Cards Reviewed</p>
          </div>
          <div class="rounded-lg border p-3">
            <p class="text-2xl font-bold text-green-500">{{ masteryPromotions }}</p>
            <p class="text-xs text-muted-foreground">Mastery Promotions</p>
          </div>
        </div>

        <Button class="mt-2" @click="handleSessionClose">Done</Button>
      </div>

      <!-- Review Card -->
      <div v-else class="space-y-4">
        <!-- Progress -->
        <Progress :model-value="progressPercent" class="h-2" />

        <!-- Word Card -->
        <ThemedCard
          :variant="currentWord.mastery_level"
          class="relative p-6"
          :border-shimmer="false"
        >
          <!-- State Badge -->
          <div class="flex items-center gap-2 mb-3">
            <Badge :variant="cardStateBadgeVariant">
              {{ cardStateLabel }}
            </Badge>
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

          <!-- Lookup Error -->
          <p v-if="isRevealed && lookupError" class="mt-4 text-sm text-destructive text-center">
            {{ lookupError }}
          </p>
        </ThemedCard>

        <!-- Quality Buttons -->
        <div v-if="isRevealed" class="space-y-2">
          <p class="text-xs text-muted-foreground text-center">How well did you recall this word?</p>
          <div class="flex justify-center gap-2">
            <template v-for="btn in qualityButtons" :key="btn.quality">
              <Button
                :variant="btn.variant"
                :disabled="isSubmitting"
                class="flex flex-col items-center gap-0.5 h-auto py-2 px-3 min-w-[4.5rem]"
                @click="handleQualitySubmit(btn.quality)"
              >
                <span class="text-sm font-medium">{{ btn.label }}</span>
                <span class="text-[10px] opacity-70">{{ formatInterval(btn.interval) }}</span>
              </Button>
            </template>
          </div>
        </div>
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { ThemedCard } from '@/components/custom/card';
import { wordlistApi, lookupApi } from '@/api';
import type { DueWordItem, ReviewResult, SM2Quality, CardState } from '@/types/wordlist';
import type { SynthesizedDictionaryEntry } from '@/types';

interface Props {
  modelValue: boolean;
  wordlistId: string;
  wordlistName: string;
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void;
  (e: 'session-complete'): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

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

// Card state display
const cardStateLabel = computed(() => {
  const state = currentWord.value?.card_state;
  const labels: Record<CardState, string> = {
    new: 'New',
    learning: 'Learning',
    young: 'Young',
    mature: 'Mature',
    relearning: 'Relearning',
  };
  return labels[state] ?? state;
});

const cardStateBadgeVariant = computed(() => {
  const state = currentWord.value?.card_state;
  if (state === 'mature') return 'default';
  if (state === 'young') return 'secondary';
  if (state === 'learning' || state === 'new') return 'outline';
  if (state === 'relearning') return 'destructive';
  return 'outline';
});

// Quality buttons based on card state
const qualityButtons = computed(() => {
  const word = currentWord.value;
  if (!word) return [];

  const intervals = word.predicted_intervals ?? {};
  const state = word.card_state;

  // Learning/Relearning: Again(0), Good(3), Easy(5)
  if (state === 'learning' || state === 'relearning' || state === 'new') {
    return [
      { quality: 0 as SM2Quality, label: 'Again', variant: 'destructive' as const, interval: intervals[0] },
      { quality: 3 as SM2Quality, label: 'Good', variant: 'default' as const, interval: intervals[3] },
      { quality: 5 as SM2Quality, label: 'Easy', variant: 'secondary' as const, interval: intervals[5] },
    ];
  }

  // Young/Mature: Again(0), Hard(2), Good(4), Easy(5)
  return [
    { quality: 0 as SM2Quality, label: 'Again', variant: 'destructive' as const, interval: intervals[0] },
    { quality: 2 as SM2Quality, label: 'Hard', variant: 'outline' as const, interval: intervals[2] },
    { quality: 4 as SM2Quality, label: 'Good', variant: 'default' as const, interval: intervals[4] },
    { quality: 5 as SM2Quality, label: 'Easy', variant: 'secondary' as const, interval: intervals[5] },
  ];
});

// Format interval in days to human-readable string
function formatInterval(intervalDays: number | undefined): string {
  if (intervalDays == null) return '';
  if (intervalDays < 1) {
    const minutes = Math.max(1, Math.round(intervalDays * 24 * 60));
    return `${minutes}min`;
  }
  return `${Math.round(intervalDays)}d`;
}

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
    dueWords.value = response.words ?? response ?? [];
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
  revealedDefinition.value = null;
}

async function handleReveal() {
  isLookingUp.value = true;
  lookupError.value = null;
  revealedDefinition.value = null;

  try {
    const entry = await lookupApi.lookup(currentWord.value.word);
    revealedDefinition.value = entry;
  } catch (err: any) {
    lookupError.value = err?.message ?? 'Failed to look up definition';
  } finally {
    isLookingUp.value = true; // keep true so button stays disabled
    isRevealed.value = true;
  }
}

async function handleQualitySubmit(quality: SM2Quality) {
  isSubmitting.value = true;
  try {
    const result: ReviewResult = await wordlistApi.submitWordReview(props.wordlistId, {
      word: currentWord.value.word,
      quality,
    });

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

function handleSessionClose() {
  emit('session-complete');
  emit('update:modelValue', false);
}
</script>
