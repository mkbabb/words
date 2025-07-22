<template>
  <div class="w-full space-y-4">
    <!-- Progress Bar -->
    <div class="relative">
      <div
        ref="progressBarRef"
        class="h-8 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
        :class="[
          'shadow-inner',
          'border border-gray-300 dark:border-gray-600',
          interactive ? 'cursor-pointer' : ''
        ]"
        @mousedown="handleMouseDown"
        @click="handleProgressBarInteraction"
      >
        <div
          class="h-full rounded-full transition-all duration-500 ease-out"
          :style="{ 
            width: `${progress}%`,
            background: rainbowGradient
          }"
          :class="['shadow-lg', progress < 100 ? 'animate-pulse' : '']"
        />
      </div>

      <!-- Checkpoint Markers -->
      <div class="absolute inset-0 flex items-center">
        <div
          v-for="(checkpoint, index) in checkpoints"
          :key="index"
          class="absolute"
          :style="{ 
            left: checkpoint.progress === 0 ? '16px' : checkpoint.progress === 100 ? 'calc(100% - 16px)' : `${checkpoint.progress}%`, 
            top: '50%',
            transform: checkpoint.progress === 0 || checkpoint.progress === 100 ? 'translateX(-50%) translateY(-50%)' : 'translateX(-50%) translateY(-50%)'
          }"
        >
          <HoverCard
            :open-delay="100"
            :close-delay="50"
          >
            <HoverCardTrigger>
              <div
                class="h-6 w-6 rounded-full border-[1.5px] transition-all duration-300 backdrop-blur-sm bg-white/20 dark:bg-gray-800/30"
                :class="[
                  progress >= checkpoint.progress
                    ? 'scale-110 border-primary/70 shadow-lg shadow-primary/20 bg-primary/10'
                    : 'border-gray-400/50 dark:border-gray-500/50',
                  interactive ? 'cursor-pointer hover:scale-125' : 'cursor-help hover:scale-125',
                ]"
                @click="handleCheckpointClick(checkpoint)"
              />
            </HoverCardTrigger>
          <HoverCardContent class="w-60" side="top" :side-offset="16" align="center" :align-offset="0">
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <h4 class="font-semibold text-sm">{{ checkpoint.label }}</h4>
                <span class="text-xs text-primary font-medium">{{ checkpoint.progress }}%</span>
              </div>
              <hr class="border-border/30">
              <p class="text-xs text-muted-foreground leading-relaxed">
                {{ getCheckpointDescription(checkpoint.progress) }}
              </p>
            </div>
          </HoverCardContent>
          </HoverCard>
        </div>
      </div>
    </div>

    <!-- Progress Percentage -->
    <div class="text-center">
      <span class="text-2xl font-bold text-gray-800 dark:text-gray-200 tracking-tight">
        {{ Math.round(progress) }}%
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { generateRainbowGradient } from '@/utils/animations'
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card'

interface Checkpoint {
  progress: number
  label: string
}

interface Props {
  progress: number
  checkpoints?: Checkpoint[]
  interactive?: boolean
}

interface Emits {
  (e: 'progress-change', progress: number): void
}

const props = withDefaults(defineProps<Props>(), {
  checkpoints: () => [
    { progress: 0, label: 'Start' },
    { progress: 10, label: 'Search' },
    { progress: 40, label: 'Fetch' },
    { progress: 50, label: 'Cluster' },
    { progress: 60, label: 'Synthesize' },
    { progress: 70, label: 'Examples' },
    { progress: 90, label: 'Save' },
    { progress: 100, label: 'Complete' },
  ],
  interactive: false,
})

const emit = defineEmits<Emits>()

const progressBarRef = ref<HTMLElement>()
const isDragging = ref(false)

const rainbowGradient = computed(() => generateRainbowGradient(8))

// Get descriptive text for checkpoint stages
const getCheckpointDescription = (progress: number): string => {
  const descriptions: Record<number, string> = {
    0: 'Pipeline initialization and setup phase. Preparing search engines and AI processing systems.',
    10: 'Searching through multiple dictionary sources including Wiktionary, Oxford, and Dictionary.com.',
    40: 'Gathering definitions from various providers and performing data validation.',
    50: 'Analyzing semantic patterns and clustering related definitions using AI.',
    60: 'Synthesizing comprehensive definitions with AI-powered meaning extraction.',
    70: 'Generating contextual usage examples and finding related terms.',
    90: 'Saving processed data to knowledge base and updating search indices.',
    100: 'Pipeline complete! Ready to display comprehensive word information.'
  }
  return descriptions[progress] || 'Processing pipeline stage...'
}

// Handle checkpoint click
const handleCheckpointClick = (checkpoint: Checkpoint) => {
  if (!props.interactive) return
  emit('progress-change', checkpoint.progress)
}

// Handle progress bar click/drag
const handleProgressBarInteraction = (event: MouseEvent) => {
  if (!props.interactive || !progressBarRef.value) return
  
  const rect = progressBarRef.value.getBoundingClientRect()
  const x = event.clientX - rect.left
  const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100))
  
  emit('progress-change', percentage)
}

// Mouse drag handlers
const handleMouseDown = (event: MouseEvent) => {
  if (!props.interactive) return
  isDragging.value = true
  handleProgressBarInteraction(event)
  
  const handleMouseMove = (e: MouseEvent) => {
    if (isDragging.value) {
      handleProgressBarInteraction(e)
    }
  }
  
  const handleMouseUp = () => {
    isDragging.value = false
    document.removeEventListener('mousemove', handleMouseMove)
    document.removeEventListener('mouseup', handleMouseUp)
  }
  
  document.addEventListener('mousemove', handleMouseMove)
  document.addEventListener('mouseup', handleMouseUp)
}
</script>