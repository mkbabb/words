<template>
  <button
    @click="handleClick"
    @mouseenter="handleHover"
    @mouseleave="handleLeave"
    :disabled="disabled || loading"
    :class="[
      'inline-flex h-8 w-8 items-center justify-center rounded-md',
      'transition-all duration-200 ease-out',
      'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100',
      variant === 'ghost' 
        ? 'hover:bg-muted/80 text-muted-foreground hover:text-foreground'
        : variant === 'subtle'
        ? 'bg-muted/30 hover:bg-muted/60 text-muted-foreground hover:text-foreground'
        : 'bg-muted hover:bg-muted/80 text-foreground'
    ]"
    :title="title || 'Refresh'"
  >
    <RefreshCw
      :size="16"
      :class="[
        'transition-transform duration-700 ease-out',
        loading && 'animate-spin'
      ]"
      :style="{
        transform: loading ? 'none' : `rotate(${rotation}deg)`,
        transition: loading ? 'none' : 'transform 700ms cubic-bezier(0.175, 0.885, 0.32, 1.4)',
      }"
    />
  </button>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'

interface Props {
  loading?: boolean
  disabled?: boolean
  variant?: 'default' | 'ghost' | 'subtle'
  title?: string
}

interface Emits {
  (e: 'click'): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  disabled: false,
  variant: 'subtle',
  title: '',
})

const emit = defineEmits<Emits>()

const rotation = ref(0)

const handleHover = () => {
  if (props.loading || props.disabled) return
  rotation.value += 180
}

const handleLeave = () => {
  if (props.loading || props.disabled) return
  rotation.value -= 180
}

const handleClick = () => {
  if (props.loading || props.disabled) return
  
  // Add a quick rotation on click for feedback
  rotation.value += 360
  emit('click')
}
</script>