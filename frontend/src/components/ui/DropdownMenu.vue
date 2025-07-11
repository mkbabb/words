<template>
  <div class="relative inline-block text-left">
    <button
      @click="isOpen = !isOpen"
      :class="cn(
        'inline-flex w-full justify-between rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50',
        props.class
      )"
    >
      <span>{{ selectedLabel || placeholder }}</span>
      <ChevronDown class="h-4 w-4 opacity-50" />
    </button>

    <div
      v-show="isOpen"
      class="absolute z-50 mt-1 w-full rounded-md border bg-popover shadow-md"
    >
      <div class="py-1">
        <button
          v-for="option in options"
          :key="option.value"
          @click="selectOption(option)"
          :class="cn(
            'block w-full px-3 py-2 text-left text-sm hover:bg-accent hover:text-accent-foreground',
            modelValue === option.value && 'bg-accent text-accent-foreground'
          )"
        >
          {{ option.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import { cn } from '@/utils'

interface Option {
  value: string
  label: string
}

interface Props {
  modelValue?: string
  options: Option[]
  placeholder?: string
  class?: any
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Select an option...'
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const isOpen = ref(false)

const selectedLabel = computed(() => {
  const selected = props.options.find(option => option.value === props.modelValue)
  return selected?.label
})

const selectOption = (option: Option) => {
  emit('update:modelValue', option.value)
  isOpen.value = false
}
</script>