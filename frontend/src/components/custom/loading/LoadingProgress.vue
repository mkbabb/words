<template>
  <div class="w-full space-y-4 gap-1 flex flex-col">
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
                class="h-6 w-6 rounded-full border-2 transition-all duration-300"
                :class="[
                  progress >= checkpoint.progress
                    ? 'scale-110 border-primary shadow-lg shadow-primary/20'
                    : 'border-gray-400 dark:border-gray-500',
                  isActiveCheckpoint(checkpoint.progress)
                    ? 'animate-pulse ring-2 ring-primary/30'
                    : '',
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
              <!-- Show current stage info if this checkpoint is active -->
              <div v-if="isActiveCheckpoint(checkpoint.progress) && stageMessage" class="mt-2 p-2 bg-primary/5 rounded border border-primary/20">
                <p class="text-xs font-medium text-primary">{{ stageMessage }}</p>
              </div>
            </div>
          </HoverCardContent>
          </HoverCard>
        </div>
      </div>
    </div>

    <!-- Progress Percentage -->
    <!-- <div class="text-center">
      <span class="text-2xl font-bold text-gray-800 dark:text-gray-200 tracking-tight">
        {{ Math.round(progress) }}%
      </span>
    </div> -->
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
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
  currentStage?: string
  stageMessage?: string
}

interface Emits {
  (e: 'progress-change', progress: number): void
}

const props = withDefaults(defineProps<Props>(), {
  checkpoints: () => [
    { progress: 0, label: 'Initialize' },
    { progress: 10, label: 'Search' },
    { progress: 15, label: 'Provider' },
    { progress: 40, label: 'Cluster' },
    { progress: 60, label: 'Synthesize' },
    { progress: 80, label: 'Storage' },
    { progress: 100, label: 'Complete' },
  ],
  interactive: false,
})

const emit = defineEmits<Emits>()

// Debug logging
watch(() => props.progress, (newVal) => {
  console.log('LoadingProgress received progress:', newVal)
})

const progressBarRef = ref<HTMLElement>()
const isDragging = ref(false)

const rainbowGradient = computed(() => generateRainbowGradient(8))

// Get descriptive text for checkpoint stages
const getCheckpointDescription = (progress: number): string => {
  const descriptions: Record<number, string> = {
    0: 'Pipeline initialization and setup phase. Preparing search engines and AI processing systems.',
    10: 'Searching through multiple dictionary sources to find the best word match.',
    15: 'Fetching definitions from dictionary providers including Wiktionary, Oxford, and Dictionary.com.',
    40: 'AI clustering analysis - grouping definitions by semantic meaning and context.',
    60: 'AI synthesis phase - creating comprehensive definitions from clustered data.',
    80: 'Saving processed entry to knowledge base and updating search indices.',
    100: 'Pipeline complete! Ready to display comprehensive word information with examples and synonyms.'
  }
  return descriptions[progress] || 'Processing pipeline stage...'
}

// Check if a checkpoint is currently active
const isActiveCheckpoint = (checkpointProgress: number): boolean => {
  // Find the current checkpoint range
  const sortedCheckpoints = props.checkpoints.sort((a, b) => a.progress - b.progress)
  const currentIndex = sortedCheckpoints.findIndex(cp => cp.progress >= props.progress)
  
  if (currentIndex === -1) {
    // Progress is beyond all checkpoints, check if this is the last one
    return checkpointProgress === sortedCheckpoints[sortedCheckpoints.length - 1].progress
  }
  
  if (currentIndex === 0) {
    // Progress is at or before first checkpoint
    return checkpointProgress === sortedCheckpoints[0].progress
  }
  
  // Progress is between checkpoints, return the previous checkpoint as active
  const activeCheckpoint = sortedCheckpoints[currentIndex - 1]
  return checkpointProgress === activeCheckpoint.progress
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