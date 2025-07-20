<template>
  <div
    class="from-background to-muted/10 border-primary/20 rounded-xl border-2 bg-gradient-to-br p-6 shadow-[0_8px_30px_rgb(0,0,0,0.12)]"
  >
    <div class="grid items-center gap-6" :class="gridClass">
      <!-- Animation Speed Control -->
      <div class="space-y-3">
        <Label class="font-mono text-sm font-medium">{{ speedLabel }}</Label>
        <Slider
          :modelValue="[speed]"
          @update:modelValue="(value) => $emit('speed-change', value?.[0] ?? 0)"
          :min="speedRange.min"
          :max="speedRange.max"
          :step="speedRange.step"
          class="w-full"
        />
        <div class="text-muted-foreground text-center text-xs">
          {{ formatSpeedDisplay(speed) }}
        </div>
      </div>

      <!-- Time/Progress Control -->
      <div class="space-y-3">
        <div class="text-center text-sm font-medium">
          {{ timeLabel }}
        </div>
        <Slider
          :modelValue="[timePosition]"
          @update:modelValue="(value) => handleTimeChange(value?.[0] ?? 0)"
          :min="timeRange.min"
          :max="timeRange.max"
          :step="timeRange.step"
          class="w-full"
        />
        <div
          class="text-muted-foreground flex items-center justify-between text-sm"
        >
          <span>{{ formatTimeDisplay(timeRange.min) }}</span>
          <span :style="{ color: getCurrentColor() }" class="font-medium">
            {{ formatTimeDisplay(timePosition) }}
          </span>
          <span>{{ formatTimeDisplay(timeRange.max) }}</span>
        </div>
      </div>

      <!-- Parameter Control (harmonics/degree) -->
      <div v-if="showParameterControl" class="space-y-3">
        <Label class="font-mono text-sm font-medium">{{
          parameterLabel
        }}</Label>
        <Slider
          :modelValue="[parameterValue]"
          @update:modelValue="(value) => $emit('parameter-change', value?.[0] ?? 0)"
          :min="parameterRange.min"
          :max="parameterRange.max"
          :step="parameterRange.step"
          class="w-full"
        />
        <div class="text-muted-foreground text-center text-xs">
          {{ formatParameterDisplay(parameterValue) }}
        </div>
      </div>
    </div>

    <!-- Play/Pause Controls -->
    <div class="border-muted/20 mt-4 flex justify-center border-t pt-3">
      <div class="flex items-center gap-6">
        <button
          @click="$emit('toggle-animation')"
          class="hover:bg-primary/10 group rounded-full p-3 transition-colors duration-200"
          :title="isAnimating ? 'Pause Animation' : 'Play Animation'"
        >
          <Play
            v-if="!isAnimating"
            class="text-primary h-6 w-6 transition-transform group-hover:scale-110"
          />
          <Pause
            v-else
            class="text-primary h-6 w-6 transition-transform group-hover:scale-110"
          />
        </button>
        <button
          @click="$emit('reset-animation')"
          class="hover:bg-muted/50 group rounded-full p-3 transition-colors duration-200"
          title="Reset Animation"
        >
          <RotateCcw
            class="text-muted-foreground h-6 w-6 transition-transform group-hover:scale-110"
          />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Play, Pause, RotateCcw } from 'lucide-vue-next';
import { Label } from '@/components/ui';
import { Slider } from '@/components/ui';

interface Props {
  // Animation state
  isAnimating: boolean;
  speed: number;
  timePosition: number;

  // Control ranges
  speedRange: { min: number; max: number; step: number };
  timeRange: { min: number; max: number; step: number };

  // Labels
  speedLabel?: string;
  timeLabel?: string;

  // Optional parameter control (harmonics/degree)
  showParameterControl?: boolean;
  parameterValue?: number;
  parameterRange?: { min: number; max: number; step: number };
  parameterLabel?: string;

  // Layout
  columns?: number;

  // Display formatters
  speedUnit?: string;
  colorMode?: 'rainbow' | 'primary' | 'none';
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
  colorMode: 'rainbow',
});

const emit = defineEmits<{
  'speed-change': [value: number];
  'time-change': [value: number];
  'parameter-change': [value: number];
  'toggle-animation': [];
  'reset-animation': [];
}>();

const gridClass = computed(() => {
  const cols = props.showParameterControl ? props.columns : props.columns - 1;
  return `grid-cols-1 md:grid-cols-${cols}`;
});

const handleTimeChange = (value: number) => {
  emit('time-change', value);
};

const formatSpeedDisplay = (speed: number): string => {
  return `${speed}${props.speedUnit}`;
};

const formatTimeDisplay = (time: number): string => {
  return time.toFixed(1);
};

const formatParameterDisplay = (param: number): string => {
  return param.toString();
};

const getCurrentColor = (): string => {
  if (props.colorMode === 'none') return 'inherit';
  if (props.colorMode === 'primary') return 'hsl(var(--primary))';

  // Rainbow mode
  const normalized =
    (props.timePosition - props.timeRange.min) /
    (props.timeRange.max - props.timeRange.min);
  const hue = normalized * 300; // Use 300 instead of 360 to avoid red overlap
  return `hsl(${hue}, 70%, 50%)`;
};
</script>
