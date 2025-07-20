<template>
  <div class="w-full max-w-lg space-y-4">
    <!-- Progress Bar -->
    <div class="relative">
      <div
        class="h-6 overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700"
        :class="[
          'shadow-inner',
          'border border-gray-300 dark:border-gray-600',
        ]"
      >
        <div
          class="h-full rounded-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 transition-all duration-500 ease-out"
          :style="{ width: `${progress}%` }"
          :class="['shadow-lg', progress < 100 ? 'animate-pulse' : '']"
        />
      </div>

      <!-- Checkpoint Markers -->
      <div class="absolute inset-0 flex items-center justify-between px-1">
        <div
          v-for="(checkpoint, index) in checkpoints"
          :key="index"
          class="group relative"
        >
          <div
            class="h-3 w-3 rounded-full border-2 transition-all duration-300"
            :class="[
              progress >= checkpoint.progress
                ? 'scale-125 border-primary shadow-lg shadow-primary/30'
                : 'border-gray-400 dark:border-gray-500',
              'cursor-help hover:scale-150',
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
interface Checkpoint {
  progress: number
  label: string
}

interface Props {
  progress: number
  checkpoints?: Checkpoint[]
}

withDefaults(defineProps<Props>(), {
  checkpoints: () => [
    { progress: 10, label: 'Search' },
    { progress: 40, label: 'Fetch' },
    { progress: 50, label: 'Cluster' },
    { progress: 60, label: 'Synthesize' },
    { progress: 70, label: 'Examples' },
    { progress: 90, label: 'Save' },
  ],
})
</script>