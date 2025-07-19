<template>
  <Modal v-model="modelValue" :close-on-backdrop="false">
    <div class="flex flex-col items-center space-y-8">
      <!-- Animated Text with Stage Lighting -->
      <AnimatedText 
        :text="word" 
        text-class="text-7xl font-black"
        :delay="500"
        :stagger="150"
        :duration="3000"
      />

      <!-- Stage Description Text -->
      <div class="max-w-md text-center">
        <p
          class="text-xl font-semibold text-gray-700 italic dark:text-gray-300"
          :class="progressTextClass"
        >
          {{ currentStageText }}
        </p>
      </div>

      <!-- Progress Component -->
      <LoadingProgress :progress="progress" />

      <!-- AI Facts Section -->
      <div
        v-if="facts.length > 0"
        class="w-full max-w-2xl space-y-4"
        :class="[
          'transition-all duration-500',
          'transform',
          facts.length > 0
            ? 'translate-y-0 opacity-100'
            : 'translate-y-4 opacity-0',
        ]"
      >
        <h3
          class="text-center text-xl font-semibold text-gray-800 dark:text-gray-200"
        >
          Interesting Facts About "{{ word }}"
        </h3>

        <div class="max-h-48 space-y-3 overflow-y-auto">
          <div
            v-for="(fact, index) in facts"
            :key="index"
            class="rounded-lg border border-white/30 bg-white/50 p-4 dark:border-white/10 dark:bg-white/5"
            :class="[
              'backdrop-blur-sm',
              'transition-all duration-300',
              'hover:bg-white/70 dark:hover:bg-white/10',
              'animate-fade-in',
            ]"
            :style="{ animationDelay: `${index * 150}ms` }"
          >
            <p class="text-sm text-gray-700 dark:text-gray-300">
              {{ fact.content }}
            </p>
            <span
              v-if="fact.category && fact.category !== 'general'"
              class="mt-2 inline-block rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
            >
              {{ fact.category }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </Modal>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import Modal from './ui/Modal.vue';
import AnimatedText from './AnimatedText.vue';
import LoadingProgress from './LoadingProgress.vue';

interface Fact {
  content: string;
  category: string;
  confidence: number;
}


interface Props {
  modelValue: boolean;
  word: string;
  progress: number;
  currentStage: string;
  facts?: Fact[];
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void;
}

const props = withDefaults(defineProps<Props>(), {
  facts: () => [],
});

const emit = defineEmits<Emits>();

// Computed properties

const currentStageText = computed(() => {
  // Handle undefined or empty stage
  if (!props.currentStage) {
    return 'Processing...';
  }

  const stageMessages: Record<string, string> = {
    // Main pipeline stages
    initialization: 'Initializing search...',
    search: 'Searching through dictionaries...',
    provider_fetch: 'Gathering definitions...',
    ai_clustering: 'Analyzing meaning patterns...',
    ai_synthesis: 'Synthesizing comprehensive definitions...',
    ai_examples: 'Generating modern usage examples...',
    ai_synonyms: 'Finding beautiful synonyms...',
    storage_save: 'Saving to knowledge base...',
    complete: 'Ready!',
    error: 'An error occurred',

    // Provider sub-stages
    provider_start: 'Connecting to dictionary providers...',
    provider_connected: 'Connected to providers...',
    provider_downloading: 'Downloading definitions...',
    provider_parsing: 'Parsing dictionary data...',
    provider_complete: 'Provider data ready...',

    // Search sub-stages
    search_exact: 'Searching for exact matches...',
    search_fuzzy: 'Trying fuzzy search...',
    search_semantic: 'Performing semantic search...',
    search_prefix: 'Searching by prefix...',
  };

  return stageMessages[props.currentStage] || 'Processing...';
});

const progressTextClass = computed(() => ({
  'animate-pulse': props.progress < 100,
  'text-green-600 dark:text-green-400': props.progress >= 100,
}));


// Pass through the model value
const modelValue = computed({
  get: () => props.modelValue,
  set: value => emit('update:modelValue', value),
});
</script>

<style scoped>
@keyframes fade-in {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.animate-fade-in {
  animation: fade-in 0.5s ease-out forwards;
  opacity: 0;
}

/* Custom scrollbar for facts */
.space-y-3::-webkit-scrollbar {
  width: 6px;
}

.space-y-3::-webkit-scrollbar-track {
  background: rgba(255, 255, 255, 0.1);
  border-radius: 3px;
}

.space-y-3::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.3);
  border-radius: 3px;
}

.space-y-3::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.5);
}
</style>
