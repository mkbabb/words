<template>
  <div class="bg-gradient-to-br from-background to-muted/10 rounded-xl p-6 shadow-[0_8px_30px_rgb(0,0,0,0.12)] border-2 border-primary/20">
    <div class="grid gap-6 items-center" :class="gridClass">
      
      <!-- Animation Speed Control -->
      <div class="space-y-3">
        <Label class="text-sm font-medium font-mono">{{ speedLabel }}</Label>
        <Slider
          :modelValue="speed"
          @update:modelValue="$emit('speed-change', $event)"
          :min="speedRange.min"
          :max="speedRange.max"
          :step="speedRange.step"
          class="w-full"
        />
        <div class="text-xs text-muted-foreground text-center">
          {{ formatSpeedDisplay(speed) }}
        </div>
      </div>

      <!-- Time/Progress Control -->
      <div class="space-y-3">
        <div class="text-sm font-medium text-center">
          {{ timeLabel }}
        </div>
        <Slider
          :modelValue="timePosition"
          @update:modelValue="handleTimeChange"
          :min="timeRange.min"
          :max="timeRange.max"
          :step="timeRange.step"
          class="w-full"
        />
        <div class="flex justify-between text-sm text-muted-foreground items-center">
          <span>{{ formatTimeDisplay(timeRange.min) }}</span>
          <span :style="{ color: getCurrentColor() }" class="font-medium">
            {{ formatTimeDisplay(timePosition) }}
          </span>
          <span>{{ formatTimeDisplay(timeRange.max) }}</span>
        </div>
      </div>

      <!-- Parameter Control (harmonics/degree) -->
      <div v-if="showParameterControl" class="space-y-3">
        <Label class="text-sm font-medium font-mono">{{ parameterLabel }}</Label>
        <Slider
          :modelValue="parameterValue"
          @update:modelValue="$emit('parameter-change', $event)"
          :min="parameterRange.min"
          :max="parameterRange.max"
          :step="parameterRange.step"
          class="w-full"
        />
        <div class="text-xs text-muted-foreground text-center">
          {{ formatParameterDisplay(parameterValue) }}
        </div>
      </div>
    </div>
    
    <!-- Play/Pause Controls -->
    <div class="flex justify-center mt-4 pt-3 border-t border-muted/20">
      <div class="flex items-center gap-6">
        <button
          @click="$emit('toggle-animation')"
          class="p-3 rounded-full hover:bg-primary/10 transition-colors duration-200 group"
          :title="isAnimating ? 'Pause Animation' : 'Play Animation'"
        >
          <Play v-if="!isAnimating" class="h-6 w-6 text-primary group-hover:scale-110 transition-transform" />
          <Pause v-else class="h-6 w-6 text-primary group-hover:scale-110 transition-transform" />
        </button>
        <button
          @click="$emit('reset-animation')"
          class="p-3 rounded-full hover:bg-muted/50 transition-colors duration-200 group"
          title="Reset Animation"
        >
          <RotateCcw class="h-6 w-6 text-muted-foreground group-hover:scale-110 transition-transform" />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Play, Pause, RotateCcw } from 'lucide-vue-next'
import Label from './Label.vue'
import Slider from './Slider.vue'

interface Props {
  // Animation state
  isAnimating: boolean
  speed: number
  timePosition: number
  
  // Control ranges
  speedRange: { min: number; max: number; step: number }
  timeRange: { min: number; max: number; step: number }
  
  // Labels
  speedLabel?: string
  timeLabel?: string
  
  // Optional parameter control (harmonics/degree)
  showParameterControl?: boolean
  parameterValue?: number
  parameterRange?: { min: number; max: number; step: number }
  parameterLabel?: string
  
  // Layout
  columns?: number
  
  // Display formatters
  speedUnit?: string
  colorMode?: 'rainbow' | 'primary' | 'none'
}

const props = withDefaults(defineProps<Props>(), {
  speedLabel: 'Animation Speed',
  timeLabel: 'Time Position',
  showParameterControl: false,
  parameterValue: 0,
  parameterRange: () => ({ min: 1, max: 50, step: 1 }),
  parameterLabel: 'Parameter',
  columns: 3,
  speedUnit: 'ms',
  colorMode: 'rainbow'
})

const emit = defineEmits<{
  'speed-change': [value: number]
  'time-change': [value: number]
  'parameter-change': [value: number]
  'toggle-animation': []
  'reset-animation': []
}>()

const gridClass = computed(() => {
  const cols = props.showParameterControl ? props.columns : props.columns - 1
  return `grid-cols-1 md:grid-cols-${cols}`
})

const handleTimeChange = (value: number) => {
  emit('time-change', value)
}

const formatSpeedDisplay = (speed: number): string => {
  return `${speed}${props.speedUnit}`
}

const formatTimeDisplay = (time: number): string => {
  return time.toFixed(1)
}

const formatParameterDisplay = (param: number): string => {
  return param.toString()
}

const getCurrentColor = (): string => {
  if (props.colorMode === 'none') return 'inherit'
  if (props.colorMode === 'primary') return 'hsl(var(--primary))'
  
  // Rainbow mode
  const normalized = (props.timePosition - props.timeRange.min) / 
                    (props.timeRange.max - props.timeRange.min)
  const hue = normalized * 300 // Use 300 instead of 360 to avoid red overlap
  return `hsl(${hue}, 70%, 50%)`
}
</script>