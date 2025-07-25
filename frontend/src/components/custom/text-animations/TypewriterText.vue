<template>
  <span
    ref="textRef"
    :class="[
      'typewriter-text',
      textureClasses,
      className
    ]"
    :style="combinedStyles"
    v-bind="$attrs"
  >
    {{ displayText }}
  </span>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useTypewriterAnimation } from '@/composables/useTextAnimations'
import { useTextureSystem } from '@/composables/useTextureSystem'
import type { TextureType, TextureIntensity } from '@/types'

interface Props {
  /** Text to animate */
  text: string
  /** Animation speed (milliseconds between characters) */
  speed?: number
  /** Delay before animation starts (ms) */
  delay?: number
  /** Auto-start animation */
  autoplay?: boolean
  /** Loop animation */
  loop?: boolean
  /** Show cursor during typing */
  cursorVisible?: boolean
  /** Cursor character */
  cursorChar?: string
  /** Pause duration after punctuation (ms) */
  pauseOnPunctuation?: number
  /** Easing function */
  easing?: string
  /** Apply texture to text */
  textureEnabled?: boolean
  /** Texture type */
  textureType?: TextureType
  /** Texture intensity */
  textureIntensity?: TextureIntensity
  /** Additional CSS classes */
  className?: string
  /** Custom styles */
  customStyles?: Record<string, string | number>
}

const props = withDefaults(defineProps<Props>(), {
  text: '',
  speed: 100, // 100ms between characters for readable typing
  delay: 0,
  autoplay: true,
  loop: false,
  cursorVisible: true,
  cursorChar: '|',
  pauseOnPunctuation: 200,
  easing: 'none',
  textureEnabled: false,
  textureType: 'clean',
  textureIntensity: 'subtle',
  className: '',
  customStyles: () => ({}),
})

// Template refs
const textRef = ref<HTMLElement | null>(null)
const textContent = ref(props.text)

// Texture system (optional)
const { textureStyles, textureClasses } = useTextureSystem({
  enabled: props.textureEnabled,
  options: {
    type: props.textureType,
    intensity: props.textureIntensity,
    blendMode: 'multiply',
    opacity: 0.02,
  },
})

// Typewriter animation
const {
  isAnimating,
  currentText,
  startAnimation,
  play,
  pause,
  restart,
} = useTypewriterAnimation(textRef, textContent, {
  speed: props.speed,
  delay: props.delay,
  autoplay: props.autoplay,
  loop: props.loop,
  easing: props.easing,
  cursorVisible: props.cursorVisible,
  cursorChar: props.cursorChar,
  pauseOnPunctuation: props.pauseOnPunctuation,
})

// Display text (either current animated text or static text)
const displayText = computed(() => {
  if (isAnimating.value) {
    return currentText.value + (props.cursorVisible ? props.cursorChar : '')
  }
  return props.text
})

// Combined styles
const combinedStyles = computed(() => ({
  ...(props.textureEnabled ? textureStyles.value : {}),
  ...props.customStyles,
  fontFamily: 'inherit',
  whiteSpace: 'pre-wrap',
}))

// Watch for text changes and restart animation
watch(() => props.text, (newText) => {
  textContent.value = newText
  if (props.autoplay) {
    restart()
  }
})

// Expose animation controls
defineExpose({
  isAnimating,
  play,
  pause,
  restart,
  startAnimation,
})
</script>

<style scoped>
.typewriter-text {
  display: inline-block;
  vertical-align: baseline;
  /* Ensure consistent cursor positioning */
  font-variant-numeric: tabular-nums;
}

/* Reduce motion support */
@media (prefers-reduced-motion: reduce) {
  .typewriter-text {
    /* Skip animation, show final text immediately */
    animation: none !important;
  }
}
</style>