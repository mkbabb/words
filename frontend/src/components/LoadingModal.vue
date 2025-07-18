<template>
  <Modal v-model="modelValue" :close-on-backdrop="false">
    <div class="flex flex-col items-center space-y-8">
      <!-- 3D Text Animation (First Pass) -->
      <div class="text-center">
        <h1
          class="text-6xl font-black chunky-3d-text select-none"
          :class="[
            'font-fraunces',
            'text-gray-900 dark:text-gray-100'
          ]"
        >
          <span
            v-for="(char, index) in displayChars"
            :key="`${word}-${index}`"
            class="inline-block char-ripple"
            :style="{ 
              animationDelay: `${index * 100}ms`,
              animationDuration: '2s'
            }"
          >
            {{ char === ' ' ? '\u00A0' : char }}
          </span>
        </h1>
      </div>

      <!-- Stage Description Text -->
      <div class="text-center max-w-md">
        <p
          class="text-lg text-gray-600 dark:text-gray-400 italic font-medium"
          :class="progressTextClass"
        >
          {{ currentStageText }}
        </p>
      </div>

      <!-- Animated Progress Bar with Checkpoints -->
      <div class="w-full max-w-lg space-y-4">
        <!-- Progress Bar -->
        <div class="relative">
          <div
            class="h-3 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden"
            :class="[
              'shadow-inner',
              'border border-gray-300 dark:border-gray-600'
            ]"
          >
            <div
              class="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 rounded-full transition-all duration-500 ease-out"
              :style="{ width: `${progress}%` }"
              :class="[
                'shadow-lg',
                'animate-pulse'
              ]"
            />
          </div>
          
          <!-- Checkpoint Markers -->
          <div class="absolute inset-0 flex justify-between items-center px-1">
            <div
              v-for="(checkpoint, index) in checkpoints"
              :key="index"
              class="w-2 h-2 rounded-full border-2 transition-all duration-300"
              :class="[
                progress >= checkpoint.progress
                  ? 'bg-white border-blue-500 scale-125 shadow-lg'
                  : 'bg-gray-300 dark:bg-gray-600 border-gray-400 dark:border-gray-500',
                'hover:scale-150 cursor-help'
              ]"
              :title="checkpoint.label"
            />
          </div>
        </div>

        <!-- Progress Percentage -->
        <div class="text-center">
          <span
            class="text-sm font-medium text-gray-500 dark:text-gray-400"
          >
            {{ Math.round(progress) }}%
          </span>
        </div>
      </div>

      <!-- AI Facts Section -->
      <div
        v-if="facts.length > 0"
        class="w-full max-w-2xl space-y-4"
        :class="[
          'transition-all duration-500',
          'transform',
          facts.length > 0 ? 'translate-y-0 opacity-100' : 'translate-y-4 opacity-0'
        ]"
      >
        <h3 class="text-xl font-semibold text-center text-gray-800 dark:text-gray-200">
          Interesting Facts About "{{ word }}"
        </h3>
        
        <div class="space-y-3 max-h-48 overflow-y-auto">
          <div
            v-for="(fact, index) in facts"
            :key="index"
            class="p-4 bg-white/50 dark:bg-white/5 rounded-lg border border-white/30 dark:border-white/10"
            :class="[
              'backdrop-blur-sm',
              'transition-all duration-300',
              'hover:bg-white/70 dark:hover:bg-white/10',
              'animate-fade-in'
            ]"
            :style="{ animationDelay: `${index * 150}ms` }"
          >
            <p class="text-sm text-gray-700 dark:text-gray-300">
              {{ fact.content }}
            </p>
            <span 
              v-if="fact.category && fact.category !== 'general'"
              class="inline-block mt-2 px-2 py-1 text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 rounded-full"
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
import { computed } from 'vue'
import Modal from './ui/Modal.vue'

interface Fact {
  content: string
  category: string
  confidence: number
}

interface Checkpoint {
  progress: number
  label: string
}

interface Props {
  modelValue: boolean
  word: string
  progress: number
  currentStage: string
  facts?: Fact[]
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  facts: () => [],
})

const emit = defineEmits<Emits>()

// Computed properties
const displayChars = computed(() => {
  return props.word.split('')
})

const currentStageText = computed(() => {
  const stageMessages: Record<string, string> = {
    'search': 'Searching through dictionaries...',
    'fetch': 'Gathering definitions...',
    'cluster': 'Analyzing meaning patterns...',
    'synthesis': 'Synthesizing comprehensive definitions...',
    'examples': 'Generating modern usage examples...',
    'synonyms': 'Finding beautiful synonyms...',
    'facts': 'Discovering fascinating facts...',
    'storage': 'Saving to knowledge base...',
    'complete': 'Ready!'
  }
  
  return stageMessages[props.currentStage] || 'Processing...'
})

const progressTextClass = computed(() => ({
  'animate-pulse': props.progress < 100,
  'text-green-600 dark:text-green-400': props.progress >= 100,
}))

// Progress checkpoints
const checkpoints: Checkpoint[] = [
  { progress: 10, label: 'Search' },
  { progress: 30, label: 'Fetch' },
  { progress: 50, label: 'Analyze' },
  { progress: 70, label: 'Synthesize' },
  { progress: 85, label: 'Enhance' },
  { progress: 100, label: 'Complete' },
]

// Pass through the model value
const modelValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})
</script>

<style scoped>
@keyframes char-ripple {
  0%, 60%, 100% {
    transform: translateY(0) scale(1);
  }
  20% {
    transform: translateY(-15px) scale(1.1);
  }
  40% {
    transform: translateY(-8px) scale(1.05);
  }
}

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

.char-ripple {
  animation: char-ripple 2s ease-in-out infinite;
}

.animate-fade-in {
  animation: fade-in 0.5s ease-out forwards;
  opacity: 0;
}

.chunky-3d-text {
  text-shadow:
    1px 1px 0 rgba(0, 0, 0, 0.2),
    2px 2px 0 rgba(0, 0, 0, 0.15),
    3px 3px 0 rgba(0, 0, 0, 0.1),
    4px 4px 0 rgba(0, 0, 0, 0.08),
    5px 5px 0 rgba(0, 0, 0, 0.05),
    0 0 20px rgba(0, 0, 0, 0.1);
  
  transition: all 0.3s ease;
}

.dark .chunky-3d-text {
  text-shadow:
    1px 1px 0 rgba(255, 255, 255, 0.1),
    2px 2px 0 rgba(255, 255, 255, 0.08),
    3px 3px 0 rgba(255, 255, 255, 0.06),
    4px 4px 0 rgba(255, 255, 255, 0.04),
    5px 5px 0 rgba(255, 255, 255, 0.02),
    0 0 20px rgba(255, 255, 255, 0.05);
}

.font-fraunces {
  font-family: 'Fraunces', serif;
  font-variation-settings: 'wght' 900;
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