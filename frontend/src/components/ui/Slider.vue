<template>
  <div class="relative flex items-center select-none touch-none w-full p-2">
    <div class="relative h-3 w-full grow overflow-hidden rounded-full bg-gray-200 dark:bg-gray-700 border border-gray-300 dark:border-gray-600">
      <div
        class="absolute h-full bg-primary rounded-full transition-all duration-200 ease-out"
        :style="{ width: `${percentage}%` }"
      />
    </div>
    <input
      type="range"
      :class="cn(
        'absolute w-full h-full opacity-0 cursor-pointer',
        props.class
      )"
      v-bind="props"
      @input="$emit('update:modelValue', Number($event.target.value))"
    />
    <div
      class="absolute h-6 w-6 rounded-full border-2 border-primary bg-white dark:bg-gray-800 shadow-lg transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:scale-110"
      :style="{ left: `calc(${percentage}% - 12px)` }"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, type InputHTMLAttributes } from 'vue'
import { cn } from '@/utils'

interface Props {
  modelValue?: number
  min?: number | string
  max?: number | string
  class?: any
  step?: number | string
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  min: 0,
  max: 100,
  modelValue: 0
})

defineEmits<{
  'update:modelValue': [value: number]
}>()

const percentage = computed(() => {
  const min = Number(props.min)
  const max = Number(props.max)
  const value = Number(props.modelValue)
  return ((value - min) / (max - min)) * 100
})
</script>