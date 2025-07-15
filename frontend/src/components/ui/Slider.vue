<template>
  <div class="relative flex w-full touch-none items-center p-2 select-none">
    <div
      class="relative h-3 w-full grow overflow-hidden rounded-full border border-gray-300 bg-gray-200 dark:border-gray-600 dark:bg-gray-700"
    >
      <div
        class="bg-primary absolute h-full rounded-full transition-all duration-200 ease-out"
        :style="{ width: `${percentage}%` }"
      />
    </div>
    <input
      type="range"
      :class="
        cn('absolute h-full w-full cursor-pointer opacity-0', props.class)
      "
      v-bind="props"
      @input="
        $emit(
          'update:modelValue',
          Number(($event.target as HTMLInputElement)?.value)
        )
      "
    />
    <div
      class="border-primary focus-visible:ring-ring absolute h-6 w-6 rounded-full border-2 bg-white shadow-lg transition-all duration-200 hover:scale-110 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 dark:bg-gray-800"
      :style="{ left: `calc(${percentage}% - 12px)` }"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { cn } from '@/utils';

interface Props {
  modelValue?: number;
  min?: number | string;
  max?: number | string;
  class?: any;
  step?: number | string;
  disabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  min: 0,
  max: 100,
  modelValue: 0,
});

defineEmits<{
  'update:modelValue': [value: number];
}>();

const percentage = computed(() => {
  const min = Number(props.min);
  const max = Number(props.max);
  const value = Number(props.modelValue);
  return ((value - min) / (max - min)) * 100;
});
</script>
