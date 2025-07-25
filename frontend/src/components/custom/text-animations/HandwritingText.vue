<template>
  <div
    :class="[
      'handwriting-container',
      className
    ]"
    :style="containerStyles"
  >
    <svg
      :width="svgWidth"
      :height="svgHeight"
      :viewBox="`0 0 ${svgWidth} ${svgHeight}`"
      class="handwriting-svg"
    >
      <!-- Background texture (optional) -->
      <defs v-if="textureEnabled">
        <pattern
          id="paper-texture"
          patternUnits="userSpaceOnUse"
          :width="60"
          :height="60"
        >
          <rect
            width="60"
            height="60"
            :fill="textureColor"
            opacity="0.02"
          />
        </pattern>
      </defs>

      <!-- Text path for handwriting animation -->
      <path
        ref="pathRef"
        :d="pathData"
        fill="none"
        :stroke="strokeColor"
        :stroke-width="strokeWidth"
        stroke-linecap="round"
        stroke-linejoin="round"
        :class="[
          'handwriting-path',
          `handwriting-${writingStyle}`,
          textureClasses
        ]"
        :style="pathStyles"
      />
    </svg>

    <!-- Fallback text for accessibility -->
    <span class="sr-only">{{ text }}</span>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useHandwritingAnimation } from '@/composables/useTextAnimations'
import { useTextureSystem } from '@/composables/useTextureSystem'
import { generateHandwritingPath } from '@/utils/textToPath'
import type { TextureType, TextureIntensity } from '@/types'

interface Props {
  /** Text to convert to handwriting animation */
  text: string
  /** Animation speed multiplier */
  speed?: number
  /** Delay before animation starts (ms) */
  delay?: number
  /** Auto-start animation */
  autoplay?: boolean
  /** Loop animation */
  loop?: boolean
  /** Writing style: pen or pencil */
  writingStyle?: 'pen' | 'pencil'
  /** Stroke width */
  strokeWidth?: number
  /** Stroke pressure (opacity) */
  pressure?: number
  /** Stroke color */
  strokeColor?: string
  /** Easing function */
  easing?: string
  /** Apply texture effects */
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
  speed: 1,
  delay: 0,
  autoplay: true,
  loop: false,
  writingStyle: 'pen',
  strokeWidth: 2,
  pressure: 0.8,
  strokeColor: 'currentColor',
  easing: 'none',
  textureEnabled: false,
  textureType: 'clean',
  textureIntensity: 'subtle',
  className: '',
  customStyles: () => ({}),
})

// Template refs
const pathRef = ref<SVGPathElement | null>(null)

// Generate path data from text
const generatedPath = computed(() => {
  return generateHandwritingPath(props.text)
})

const pathData = computed(() => generatedPath.value.path)
const svgWidth = computed(() => generatedPath.value.width)  
const svgHeight = computed(() => generatedPath.value.height)

// Texture system (optional)
const { textureStyles, textureClasses } = useTextureSystem({
  enabled: props.textureEnabled,
  options: {
    type: props.textureType,
    intensity: props.textureIntensity,
    blendMode: 'multiply',
    opacity: 0.03,
  },
})

// Handwriting animation
const {
  isAnimating,
  startAnimation,
  play,
  pause,
  restart,
} = useHandwritingAnimation(pathRef, {
  speed: props.speed,
  delay: props.delay,
  autoplay: props.autoplay,
  loop: props.loop,
  easing: props.easing,
  strokeWidth: props.strokeWidth,
  pressure: props.pressure,
  style: props.writingStyle,
})

// Computed styles
const textureColor = computed(() => {
  return props.strokeColor === 'currentColor' ? 'currentColor' : props.strokeColor
})

const containerStyles = computed(() => ({
  ...props.customStyles,
  display: 'inline-block',
  verticalAlign: 'baseline',
}))

const pathStyles = computed(() => {
  const baseStyles: Record<string, string | number> = {
    opacity: props.pressure,
  }

  // Add texture effects if enabled
  if (props.textureEnabled) {
    Object.assign(baseStyles, textureStyles.value)
  }

  // Add writing style specific effects
  if (props.writingStyle === 'pencil') {
    baseStyles.filter = 'blur(0.5px)'
    baseStyles.strokeDasharray = '0.5,0.5'
  }

  return baseStyles
})

// Watch for text changes
watch(() => props.text, () => {
  if (props.autoplay && pathRef.value) {
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
.handwriting-container {
  line-height: 1;
}

.handwriting-svg {
  display: block;
  max-width: 100%;
  height: auto;
}

.handwriting-path {
  transition: filter 0.2s ease;
}

/* Pen style - clean, consistent strokes */
.handwriting-pen {
  stroke-linecap: round;
  stroke-linejoin: round;
}

/* Pencil style - textured, variable opacity */
.handwriting-pencil {
  stroke-linecap: round;
  stroke-linejoin: round;
  filter: blur(0.3px);
}

/* Accessibility */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .handwriting-path {
    stroke-dasharray: none !important;
    stroke-dashoffset: 0 !important;
    animation: none !important;
  }
}
</style>