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
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { gsap } from 'gsap'
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

// Animation state
const isAnimating = ref(false)
const currentText = ref('')
const cursorVisible = ref(true)
let timeline: gsap.core.Timeline | null = null
let cursorTimeline: gsap.core.Timeline | null = null

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

// Typewriter animation logic
const startAnimation = async () => {
  if (!textRef.value || isAnimating.value) return

  isAnimating.value = true
  currentText.value = ''
  
  await nextTick()

  // Create main timeline
  timeline = gsap.timeline({
    paused: !props.autoplay,
    delay: props.delay / 1000,
    repeat: props.loop ? -1 : 0,
  })

  const chars = textContent.value.split('')
  const charDuration = props.speed / 1000 // Convert milliseconds to seconds for GSAP

  chars.forEach((char, index) => {
    timeline!.call(() => {
      currentText.value = textContent.value.slice(0, index + 1)
      if (textRef.value) {
        textRef.value.textContent = currentText.value + (props.cursorVisible ? props.cursorChar : '')
      }
    })

    // Add pause after punctuation
    const isPunctuation = /[.!?,:;]/.test(char)
    const delay = isPunctuation ? props.pauseOnPunctuation / 1000 : 0

    timeline!.to({}, { duration: charDuration + delay })
  })

  // Remove cursor at end
  timeline.call(() => {
    if (textRef.value && props.cursorVisible) {
      textRef.value.textContent = currentText.value
    }
    isAnimating.value = false
  })

  if (props.autoplay) {
    timeline.play()
  }
}

const startCursorBlink = () => {
  if (!props.cursorVisible) return
  
  cursorTimeline = gsap.timeline({ repeat: -1, yoyo: true })
  cursorTimeline.to(cursorVisible, { 
    duration: 0.5, 
    delay: 0.5,
    onUpdate: () => {
      if (textRef.value && isAnimating.value) {
        const cursor = cursorVisible.value ? props.cursorChar : ''
        textRef.value.textContent = currentText.value + cursor
      }
    }
  })
}

const play = () => timeline?.play()
const pause = () => timeline?.pause()
const restart = () => {
  timeline?.restart()
  startAnimation()
}

const cleanup = () => {
  timeline?.kill()
  cursorTimeline?.kill()
  timeline = null
  cursorTimeline = null
}

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

// Lifecycle hooks
onMounted(() => {
  if (props.autoplay) {
    startAnimation()
  }
  startCursorBlink()
})

onUnmounted(cleanup)

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