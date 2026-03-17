<template>
  <button
    @click="handleClick"
    @mouseenter="handleHover"
    @mouseleave="handleLeave"
    :disabled="disabled || loading"
    :class="[
      'inline-flex h-8 w-8 items-center justify-center rounded-full',
      'transition-all duration-200 ease-out',
      'hover:scale-105 focus-visible:ring-2 focus-visible:ring-primary/50 focus-visible:outline-none',
      'disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100',
      variant === 'ghost'
        ? 'bg-card/40 backdrop-blur-sm border border-border/20 text-muted-foreground hover:bg-card/70 hover:text-foreground hover:border-border/40'
        : variant === 'subtle'
        ? 'bg-card/50 backdrop-blur-sm border border-border/25 text-muted-foreground hover:bg-card/75 hover:text-foreground hover:border-border/45 shadow-sm'
        : 'bg-card/60 backdrop-blur-sm border border-border/30 text-foreground hover:bg-card/85 hover:border-border/50 shadow-sm'
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