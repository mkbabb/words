<template>
  <span
    :class="computedClass"
    :style="computedStyle"
    role="status"
    aria-live="polite"
  >
    <slot>{{ text }}</slot>
  </span>
  
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  text?: string
  textClass?: string
  /** Duration in ms for one sweep */
  duration?: number
  /** Delay in ms before starting */
  delay?: number
  /** If provided, applies Tailwind gradient classes to control colors (e.g. 'from-amber-400/20 via-white/90 to-amber-600/20') */
  gradientClass?: string | null
  /** Reverse sweep direction */
  reverse?: boolean
  /** Disable animation (e.g. for reduced motion) */
  disabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  text: '',
  textClass: '',
  duration: 2000,
  delay: 0,
  gradientClass: null,
  reverse: false,
  disabled: false,
})

const computedClass = computed(() => {
  // If gradientClass provided, use gradient-based shimmer
  if (props.gradientClass) {
    return [
      props.textClass,
      'bg-clip-text text-transparent bg-gradient-to-r',
      // Allow consumer control with Tailwind utilities
      props.gradientClass,
      props.disabled ? '' : 'animate-[shimmer-sweep_var(--shimmer-duration)_ease-in-out_infinite] bg-[length:200%_100%]'
    ].filter(Boolean).join(' ')
  }
  // Default to CSS utility defined in assets/index.css
  return [props.textClass, props.disabled ? '' : 'shimmer-text'].filter(Boolean).join(' ')
})

const computedStyle = computed(() => {
  const style: Record<string, string> = {}
  // Control animation timing using CSS var for both modes
  style['--shimmer-duration'] = `${props.duration}ms`
  if (props.delay) style.animationDelay = `${props.delay}ms`
  if (props.reverse) style.animationDirection = 'reverse'
  return style
})
</script>

<style scoped>
/* Fallback keyframes to ensure animation name resolves even if tree-shaken */
@keyframes shimmer-sweep { from { background-position: -200% 0; } to { background-position: 200% 0; } }
</style>
