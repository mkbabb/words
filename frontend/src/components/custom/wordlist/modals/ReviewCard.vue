<template>
  <div class="space-y-4">
    <!-- Progress bar -->
    <div class="h-1 w-full overflow-hidden rounded-full bg-muted/40">
      <div
        class="h-full rounded-full review-progress-gradient"
        :style="{ width: `${progressRatio * 100}%` }"
      />
    </div>

    <!-- Review Card (no flip — crossfade between front/back) -->
    <div
      @touchstart="onTouchStart"
      @touchmove="onTouchMove"
      @touchend="onTouchEnd"
      :style="isSwiping ? { transform: `translateX(${touchDelta.x * 0.3}px) rotate(${touchDelta.x * 0.05}deg)`, opacity: 1 - Math.abs(touchDelta.x) / 300, transition: 'none' } : { transition: 'transform 0.3s ease, opacity 0.3s ease' }"
    >
      <ThemedCard
        :variant="currentWord.mastery_level"
        class="relative"
        :border-shimmer="true"
      >
        <!-- Front: Word only (pre-reveal) -->
        <Transition name="card-fade" mode="out-in">
          <div v-if="!isFlipped" key="front" class="p-5">
            <!-- State Badge -->
            <div class="flex items-center gap-2 mb-2">
              <span
                :class="['inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', stateBadgeClasses]"
              >
                {{ stateLabel }}
              </span>
              <Badge v-if="currentWord.is_leech" variant="destructive" class="text-xs">
                Leech
              </Badge>
            </div>

            <!-- Word -->
            <p class="text-heading text-center py-6">
              {{ currentWord.word }}
            </p>

            <!-- Notes -->
            <p v-if="currentWord.notes" class="text-xs text-muted-foreground text-center italic mb-2">
              {{ currentWord.notes }}
            </p>

            <!-- Reveal Button -->
            <div class="flex justify-center mt-2">
              <Button
                :disabled="isLookingUp"
                @click="$emit('reveal')"
                class="relative overflow-hidden"
              >
                <span v-if="isLookingUp" class="flex items-center gap-2">
                  Looking up...
                </span>
                <span v-else>Reveal <kbd class="ml-1 text-[10px] opacity-50 border rounded px-1">Space</kbd></span>
                <span
                  v-if="isLookingUp"
                  class="absolute bottom-0 left-0 right-0 h-0.5 rainbow-shimmer"
                />
              </Button>
            </div>
          </div>

          <!-- Back: Definition (post-reveal) -->
          <div v-else key="back" class="p-5 max-h-[55dvh] overflow-y-auto scrollbar-thin">
            <!-- Word (compact, top-aligned) -->
            <div class="flex items-center justify-between gap-2 mb-1">
              <p class="text-lg font-serif font-bold">
                {{ currentWord.word }}
              </p>
              <span
                :class="['inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium flex-shrink-0', stateBadgeClasses]"
              >
                {{ stateLabel }}
              </span>
            </div>

            <!-- Definition Preview -->
            <div v-if="revealedDefinition" class="space-y-2 text-sm border-t border-border/30 pt-3 mt-2">
              <ul class="list-disc list-inside space-y-1.5">
                <li
                  v-for="(def, j) in revealedDefinition.definitions?.slice(0, 8)"
                  :key="j"
                  class="text-foreground/90 leading-relaxed"
                >
                  {{ def.text }}
                </li>
              </ul>
            </div>

            <!-- Lookup Timed Out -->
            <div
              v-if="lookupTimedOut"
              class="mt-4 text-sm text-center cursor-pointer rounded-lg border border-amber-500/30 bg-amber-500/10 p-3 text-amber-500 hover:bg-amber-500/15 transition-colors"
              @click="$emit('reveal')"
            >
              Lookup timed out — tap to retry
            </div>

            <!-- Lookup Error (non-timeout) -->
            <div v-else-if="lookupError" class="mt-4 text-sm text-center rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-destructive">
              {{ lookupError }}
            </div>

            <!-- No definition found -->
            <div v-else-if="!revealedDefinition && !lookupTimedOut && !lookupError" class="mt-4 py-6 text-center text-muted-foreground text-sm">
              No definition available
            </div>
          </div>
        </Transition>
      </ThemedCard>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Button, Badge } from '@mkbabb/glass-ui';
import { ThemedCard } from '@/components/custom/card';
import type { DueWordItem, SM2Quality } from '@/types/wordlist';
import type { SynthesizedDictionaryEntry } from '@/types';

interface Props {
  currentWord: DueWordItem;
  isFlipped: boolean;
  isLookingUp: boolean;
  revealedDefinition: SynthesizedDictionaryEntry | null;
  lookupTimedOut: boolean;
  lookupError: string | null;
  isRevealed: boolean;
  stateLabel: string;
  stateBadgeClasses: string;
  progressRatio: number;
}

interface Emits {
  (e: 'reveal'): void;
  (e: 'swipe-quality', quality: SM2Quality): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

// Swipe gesture state
const touchStart = ref({ x: 0, y: 0 });
const touchDelta = ref({ x: 0, y: 0 });
const isSwiping = ref(false);

function onTouchStart(e: TouchEvent) {
  touchStart.value = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  isSwiping.value = true;
}

function onTouchMove(e: TouchEvent) {
  if (!isSwiping.value) return;
  touchDelta.value = {
    x: e.touches[0].clientX - touchStart.value.x,
    y: e.touches[0].clientY - touchStart.value.y,
  };
}

function onTouchEnd() {
  if (!isSwiping.value) return;
  const threshold = 80;
  if (props.isRevealed) {
    if (Math.abs(touchDelta.value.x) > threshold) {
      if (touchDelta.value.x < 0) emit('swipe-quality', 0 as SM2Quality); // swipe left = Again
      else emit('swipe-quality', 4 as SM2Quality); // swipe right = Good
    } else if (touchDelta.value.y < -threshold) {
      emit('swipe-quality', 5 as SM2Quality); // swipe up = Easy
    }
  }
  touchDelta.value = { x: 0, y: 0 };
  isSwiping.value = false;
}
</script>
