<template>
  <Dialog
    :open="modelValue"
    @update:open="emit('update:modelValue', $event)"
  >
      <DialogContent
        class="max-w-md p-0"
        @pointer-down-outside.prevent
        @close-auto-focus.prevent
      >
        <DialogTitle class="sr-only">Word Detail</DialogTitle>

        <div v-if="word" class="p-6">
          <!-- Close button -->
          <DialogClose
            class="absolute top-4 right-4 rounded-sm opacity-50 transition-opacity hover:opacity-100 outline-none"
          >
            <X :size="16" />
          </DialogClose>

          <!-- Word title — clickable for lookup -->
          <button
            class="text-heading sm:text-title text-left
                   decoration-primary/40 underline-offset-[6px] decoration-1
                   hover:underline cursor-pointer
                   outline-none transition-fast"
            @click="emit('lookup', word.word)"
          >
            {{ word.word?.toLowerCase() ?? '' }}
          </button>

          <!-- Badges row -->
          <div class="flex items-center gap-2 mt-3">
            <span
              v-if="stateLabel"
              :class="['inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', stateBadgeClasses]"
            >
              {{ stateLabel }}
            </span>
            <span
              v-if="word.temperature === 'hot'"
              class="status-badge status-badge-hot"
            >
              <Flame class="h-3 w-3" />
              Hot
            </span>
            <span
              v-else-if="word.temperature === 'cold' && word.review_data?.repetitions > 0"
              class="status-badge status-badge-cold"
            >
              <Snowflake class="h-3 w-3" />
              Cold
            </span>
            <span
              v-if="isDueForReview"
              class="status-badge status-badge-due"
            >
              Due
            </span>
            <span
              v-if="word.review_data?.is_leech"
              class="status-badge status-badge-leech"
            >
              Leech
            </span>
          </div>

          <!-- Stats grid — flat key-value rows -->
          <div class="mt-5 grid grid-cols-1 gap-3 text-sm font-serif sm:grid-cols-2">
            <div class="card-surface flex items-center justify-between px-4 py-3">
              <span class="text-muted-foreground">Reviews</span>
              <span class="font-medium tabular-nums">{{ word.review_data?.repetitions ?? 0 }}</span>
            </div>
            <div class="card-surface flex items-center justify-between px-4 py-3">
              <span class="text-muted-foreground">Ease</span>
              <span class="font-medium tabular-nums">{{ (word.review_data?.ease_factor ?? 2.5).toFixed(1) }}</span>
            </div>
            <div class="card-surface flex items-center justify-between px-4 py-3">
              <span class="text-muted-foreground">Interval</span>
              <span class="font-medium tabular-nums">{{ formatInterval(word.review_data?.interval ?? 0) }}</span>
            </div>
            <div class="card-surface flex items-center justify-between px-4 py-3">
              <span class="text-muted-foreground">Lapses</span>
              <span class="font-medium tabular-nums">{{ word.review_data?.lapse_count ?? 0 }}</span>
            </div>
          </div>

          <!-- Timeline -->
          <div class="card-surface mt-4 space-y-3 p-4 text-sm font-serif">
            <div class="flex justify-between gap-4">
              <span class="text-muted-foreground">Added</span>
              <span>{{ formatRelativeTime(word.added_date) }}</span>
            </div>
            <div v-if="word.last_visited" class="flex justify-between gap-4">
              <span class="text-muted-foreground">Last visited</span>
              <span>{{ formatRelativeTime(word.last_visited) }}</span>
            </div>
            <div class="flex justify-between gap-4">
              <span class="text-muted-foreground">Next review</span>
              <span :class="isDueForReview ? 'font-medium text-primary' : ''">
                {{ formatRelativeTime(word.review_data?.next_review_date) }}
              </span>
            </div>
          </div>

          <!-- Notes -->
          <div v-if="word.notes" class="card-surface mt-4 p-4">
            <div class="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5">Notes</div>
            <p class="text-sm font-serif leading-relaxed text-foreground/90">{{ word.notes }}</p>
          </div>

          <!-- Tags -->
          <div v-if="word.tags?.length > 0" class="mt-3 flex flex-wrap gap-1.5">
            <span
              v-for="tag in word.tags"
              :key="tag"
              class="inline-block rounded-full bg-muted px-2.5 py-0.5 text-xs font-medium"
            >
              {{ tag }}
            </span>
          </div>

          <!-- Divider + Actions -->
          <div class="border-t border-border/40 mt-5 pt-4 flex items-center gap-2">
            <Button size="sm" @click="emit('review')">
              <BookOpen class="mr-1.5 h-3.5 w-3.5" />
              Review
            </Button>
            <Button size="sm" variant="outline" @click="handleEditNotes">
              <Edit2 class="mr-1.5 h-3.5 w-3.5" />
              Edit Notes
            </Button>
            <Button
              size="sm"
              variant="ghost"
              class="text-destructive hover:text-destructive ml-auto"
              :disabled="isRemoving"
              @click="handleRemove"
            >
              <Trash2 class="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
      </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { BookOpen, Edit2, Flame, Snowflake, Trash2, X } from 'lucide-vue-next';
import {
  Dialog,
  DialogContent,
  DialogClose,
  DialogTitle,
  Button,
} from '@mkbabb/glass-ui';
import { wordlistApi } from '@/api';
import type { WordListItem } from '@/types';
import { formatRelativeTime } from '@/utils';
import {
  formatInterval,
  getCardStateLabel,
  getCardStateBadgeClasses,
} from '../utils/formatting';

interface Props {
  modelValue: boolean;
  word: WordListItem | null;
  wordlistId: string;
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void;
  (e: 'lookup', word: string): void;
  (e: 'review'): void;
  (e: 'edit', word: WordListItem): void;
  (e: 'remove', word: WordListItem): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const isRemoving = ref(false);
const savedScrollY = ref(0);

// Save scroll position on open, restore on close
watch(() => props.modelValue, (open) => {
  if (open) {
    savedScrollY.value = window.scrollY;
    document.body.style.overflow = 'hidden';
  } else {
    document.body.style.overflow = '';
    // Wait for dialog close animation (~300ms) before restoring scroll
    setTimeout(() => window.scrollTo(0, savedScrollY.value), 320);
  }
});

const stateLabel = computed(() =>
  getCardStateLabel(props.word?.review_data?.card_state)
);

const stateBadgeClasses = computed(() =>
  getCardStateBadgeClasses(props.word?.review_data?.card_state)
);

const isDueForReview = computed(() => {
  const reviewDate = props.word?.review_data?.next_review_date;
  if (!reviewDate) return false;
  return new Date(reviewDate) <= new Date();
});

function handleEditNotes() {
  if (!props.word) return;
  emit('update:modelValue', false);
  emit('edit', props.word);
}

async function handleRemove() {
  if (!props.word || !props.wordlistId) return;
  isRemoving.value = true;
  try {
    await wordlistApi.removeWord(props.wordlistId, props.word.word);
    emit('remove', props.word);
    emit('update:modelValue', false);
  } catch {
    // Error handled by caller
  } finally {
    isRemoving.value = false;
  }
}
</script>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  border-radius: 9999px;
  padding: 0.125rem 0.5rem;
  font-size: var(--type-caption);
  font-weight: 500;
}

.status-badge-hot {
  border: 1px solid color-mix(in srgb, #f59e0b 20%, transparent);
  background: color-mix(in srgb, #f59e0b 10%, transparent);
  color: rgb(217 119 6);
}

.status-badge-cold {
  border: 1px solid color-mix(in srgb, #0ea5e9 20%, transparent);
  background: color-mix(in srgb, #0ea5e9 10%, transparent);
  color: rgb(2 132 199);
}

.status-badge-due {
  border: 1px solid color-mix(in srgb, var(--color-primary) 20%, transparent);
  background: color-mix(in srgb, var(--color-primary) 10%, transparent);
  color: var(--color-primary);
}

.status-badge-leech {
  border: 1px solid color-mix(in srgb, var(--color-destructive) 20%, transparent);
  background: color-mix(in srgb, var(--color-destructive) 10%, transparent);
  color: var(--color-destructive);
}

:global(.dark) .status-badge-hot {
  color: rgb(251 191 36);
}

:global(.dark) .status-badge-cold {
  color: rgb(56 189 248);
}
</style>
