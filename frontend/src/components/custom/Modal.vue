<template>
  <Dialog
    :open="modelValue"
    @update:open="emit('update:modelValue', $event)"
  >
    <DialogContent
      :class="['modal-dialog-content flex flex-col overflow-hidden', maxWidthClass, maxHeightClass]"
      @pointer-down-outside="handlePointerDownOutside"
      @escape-key-down="handleEscapeKeyDown"
      @close-auto-focus.prevent
    >
      <div class="modal-scroll flex-1" :class="paddingClass">
        <slot />
      </div>
    </DialogContent>
  </Dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Dialog, DialogContent } from '@mkbabb/glass-ui'

interface Props {
  modelValue: boolean
  closeOnBackdrop?: boolean
  maxWidth?: 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl' | '4xl' | '5xl'
  maxHeight?: 'sm' | 'md' | 'lg' | 'xl' | 'screen' | 'viewport'
  padding?: 'sm' | 'md' | 'lg' | 'xl'
}

interface Emits {
  (e: 'update:modelValue', value: boolean): void
}

const props = withDefaults(defineProps<Props>(), {
  closeOnBackdrop: true,
  maxWidth: '3xl',
  maxHeight: 'viewport',
  padding: 'lg',
})

const emit = defineEmits<Emits>()

const maxWidthClass = computed(() => {
  const widthMap = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    '4xl': 'max-w-4xl',
    '5xl': 'max-w-5xl',
  }

  return widthMap[props.maxWidth]
})

const maxHeightClass = computed(() => {
  const heightMap = {
    sm: 'max-h-96',
    md: 'max-h-[32rem]',
    lg: 'max-h-[40rem]',
    xl: 'max-h-[48rem]',
    screen: 'max-h-screen',
    viewport: 'max-h-[calc(100svh-2rem)]',
  }

  return heightMap[props.maxHeight]
})

const paddingClass = computed(() => {
  const paddingMap = {
    sm: 'p-4',
    md: 'p-6',
    lg: 'p-8',
    xl: 'p-10',
  }

  return paddingMap[props.padding]
})

const handlePointerDownOutside = (event: Event) => {
  if (!props.closeOnBackdrop) {
    event.preventDefault()
  }
}

const handleEscapeKeyDown = (event: KeyboardEvent) => {
  if (!props.closeOnBackdrop) {
    event.preventDefault()
  }
}
</script>

<style scoped>
.modal-scroll {
  overflow-y: auto;
}
</style>
