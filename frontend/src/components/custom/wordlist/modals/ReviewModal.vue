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
        <!-- Backdrop -- fully opaque to prevent bleed-through -->
        <div
          ref="backdropRef"
          class="dialog-overlay absolute inset-0"
        />

        <!-- Close button -->
        <button
          class="absolute top-4 right-4 z-controls flex h-8 w-8 items-center justify-center rounded-full glass-subtle text-foreground/70 transition-colors hover:bg-background/90 hover:text-foreground"
          @click.stop="session.handleClose"
        >
          <X :size="16" />
        </button>

        <!-- Content card -->
        <div
          ref="contentRef"
          class="dialog-surface paper-texture-overlay relative z-content mx-4 max-h-[90svh] w-full max-w-3xl overflow-y-auto p-8 scrollbar-thin"
          @click.stop
        >
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
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, toRef } from 'vue';
import { X } from 'lucide-vue-next';
import { Button } from '@mkbabb/glass-ui';
import yoshiYellowStanding from '@/assets/yoshi/standing/yoshi_yellow_standing.png';
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

// Animation refs
const backdropRef = ref<HTMLDivElement>();
const contentRef = ref<HTMLDivElement>();

// Writable computed for v-model
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

function handleBackdropClick(event: Event) {
  const target = event.target as Element;
  if (target === event.currentTarget || target === backdropRef.value) {
    session.handleClose();
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

    backdropRef.value.style.transition = 'opacity 200ms cubic-bezier(0.4, 0, 0.2, 1)';
    backdropRef.value.style.opacity = '1';

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
  transition: opacity 0.25s var(--ease-standard),
              transform 0.25s var(--ease-standard);
}
.card-fade-leave-active {
  transition: opacity 0.15s var(--ease-standard),
              transform 0.15s var(--ease-standard);
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
  100% { transform: translateY(100dvh) rotate(720deg); opacity: 0; }
}

.confetti-piece {
  position: fixed;
  width: 8px;
  height: 8px;
  border-radius: 2px;
  z-index: var(--z-overlay, 50);
  pointer-events: none;
  animation: confetti-fall 2s ease-in forwards;
}
</style>
