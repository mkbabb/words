<template>
  <div class="w-full max-w-lg space-y-4">
    <!-- Progress Bar -->
    <div class="relative">
      <div
        ref="progressBarRef"
        class="h-6 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
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
      <div class="absolute inset-0 flex items-center justify-between px-1">
        <div
          v-for="(checkpoint, index) in checkpoints"
          :key="index"
          class="group relative"
          @click="handleCheckpointClick(checkpoint)"
        >
          <div
            class="h-3 w-3 rounded-full border-2 transition-all duration-300"
            :class="[
              progress >= checkpoint.progress
                ? 'scale-125 border-primary shadow-lg shadow-primary/30'
                : 'border-gray-400 dark:border-gray-500',
              interactive ? 'cursor-pointer hover:scale-150' : 'cursor-help hover:scale-150',
            ]"
          />
          <!-- Tooltip -->
          <div
            class="pointer-events-none absolute bottom-full left-1/2 z-50 mb-3 -translate-x-1/2 whitespace-nowrap opacity-0 transition-all duration-300 group-hover:opacity-100 group-hover:translate-y-[-2px]"
          >
            <div class="rounded-lg border border-white/20 bg-white/90 dark:bg-gray-900/90 backdrop-blur-md px-3 py-1.5 shadow-xl">
              <span class="text-xs font-medium text-gray-800 dark:text-gray-200">{{ checkpoint.label }}</span>
              <div class="absolute top-full left-1/2 -mt-[1px] h-0 w-0 -translate-x-1/2">
                <div class="border-t-8 border-r-8 border-l-8 border-t-white/90 dark:border-t-gray-900/90 border-r-transparent border-l-transparent" />
              </div>
            </div>
          </div>
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
    { progress: 10, label: 'Search' },
    { progress: 40, label: 'Fetch' },
    { progress: 50, label: 'Cluster' },
    { progress: 60, label: 'Synthesize' },
    { progress: 70, label: 'Examples' },
    { progress: 90, label: 'Save' },
  ],
  interactive: false,
})

const emit = defineEmits<Emits>()

const progressBarRef = ref<HTMLElement>()
const isDragging = ref(false)

const rainbowGradient = computed(() => generateRainbowGradient(8))

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