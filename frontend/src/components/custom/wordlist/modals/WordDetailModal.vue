<template>
  <DialogRoot
    :open="modelValue"
    @update:open="emit('update:modelValue', $event)"
  >
    <DialogPortal>
      <!-- Frosted glass overlay (TimeMachine-style) -->
      <DialogOverlay
        class="fixed inset-0 z-50 bg-background/50 backdrop-blur-lg
               data-[state=open]:animate-in data-[state=closed]:animate-out
               data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0
               duration-300"
      />

      <!-- Content panel -->
      <DialogContent
        class="fixed top-[50%] left-[50%] z-50 w-full max-w-[calc(100%-2rem)] sm:max-w-md
               translate-x-[-50%] translate-y-[-50%] rounded-xl border border-border/40
               bg-background p-0 shadow-2xl outline-none
               data-[state=open]:animate-in data-[state=closed]:animate-out
               data-[state=open]:fade-in-0 data-[state=closed]:fade-out-0
               data-[state=open]:zoom-in-95 data-[state=closed]:zoom-out-95
               duration-300"
        @pointer-down-outside.prevent
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
            class="text-2xl sm:text-3xl font-serif font-bold text-left
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
              v-if="isDueForReview"
              class="inline-flex items-center rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary"
            >
              Due
            </span>
            <span
              v-if="word.review_data?.is_leech"
              class="inline-flex items-center rounded-full bg-destructive/10 px-2 py-0.5 text-xs font-medium text-destructive"
            >
              Leech
            </span>
          </div>

          <!-- Stats grid — flat key-value rows -->
          <div class="grid grid-cols-2 gap-x-8 gap-y-1.5 mt-5 text-sm font-serif">
            <div class="flex justify-between">
              <span class="text-muted-foreground">Reviews</span>
              <span class="font-medium tabular-nums">{{ word.review_data?.repetitions ?? 0 }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-muted-foreground">Ease</span>
              <span class="font-medium tabular-nums">{{ (word.review_data?.ease_factor ?? 2.5).toFixed(1) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-muted-foreground">Interval</span>
              <span class="font-medium tabular-nums">{{ formatInterval(word.review_data?.interval ?? 0) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-muted-foreground">Lapses</span>
              <span class="font-medium tabular-nums">{{ word.review_data?.lapse_count ?? 0 }}</span>
            </div>
          </div>

          <!-- Timeline -->
          <div class="mt-4 space-y-1.5 text-sm font-serif border-t border-border/30 pt-4">
            <div class="flex justify-between">
              <span class="text-muted-foreground">Added</span>
              <span>{{ formatRelativeTime(word.added_date) }}</span>
            </div>
            <div v-if="word.last_visited" class="flex justify-between">
              <span class="text-muted-foreground">Last visited</span>
              <span>{{ formatRelativeTime(word.last_visited) }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-muted-foreground">Next review</span>
              <span :class="isDueForReview ? 'font-medium text-primary' : ''">
                {{ formatRelativeTime(word.review_data?.next_review_date) }}
              </span>
            </div>
          </div>

          <!-- Notes -->
          <div v-if="word.notes" class="mt-4 border-t border-border/30 pt-4">
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
    </DialogPortal>
  </DialogRoot>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { BookOpen, Edit2, Trash2, X } from 'lucide-vue-next';
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogClose,
  DialogTitle,
} from 'reka-ui';
import { Button } from '@/components/ui/button';
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
