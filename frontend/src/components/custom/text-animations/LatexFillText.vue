<template>
  <div
    ref="containerRef"
    :class="[
      'latex-fill-container',
      textureClasses,
      className
    ]"
    :style="containerStyles"
  >
    <!-- LaTeX content container -->
    <div
      ref="contentRef"
      :class="[
        'latex-content',
        { 'math-mode': mathMode }
      ]"
      :style="contentStyles"
    >
      <!-- LaTeX component integration -->
      <LaTeX
        v-if="mathMode && latexExpression"
        :expression="latexExpression"
        :class="latexClasses"
      />
      <span
        v-else
        v-html="formattedContent"
      />
    </div>

    <!-- Animation overlay mask -->
    <div
      v-if="isAnimating"
      ref="maskRef"
      class="latex-mask"
      :style="maskStyles"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useLatexFillAnimation } from '@/composables/useTextAnimations'
import { useTextureSystem } from '@/composables/useTextureSystem'
import { LaTeX } from '@/components/custom/latex'
import type { TextureType, TextureIntensity } from '@/types'

interface Props {
  /** Content to animate (LaTeX expression or HTML) */
  content: string
  /** LaTeX expression (when mathMode is true) */
  latexExpression?: string
  /** Animation speed */
  speed?: number
  /** Delay before animation starts (ms) */
  delay?: number
  /** Auto-start animation */
  autoplay?: boolean
  /** Loop animation */
  loop?: boolean
  /** Fill direction */
  fillDirection?: 'left-to-right' | 'top-to-bottom' | 'center-out'
  /** Enable math mode (uses LaTeX component) */
  mathMode?: boolean
  /** Easing function */
  easing?: string
  /** Apply texture effects */
  textureEnabled?: boolean
  /** Texture type */
  textureType?: TextureType
  /** Texture intensity */
  textureIntensity?: TextureIntensity
  /** Background color for mask */
  maskColor?: string
  /** Additional CSS classes */
  className?: string
  /** Additional CSS classes for LaTeX component */
  latexClasses?: string
  /** Custom styles */
  customStyles?: Record<string, string | number>
}

const props = withDefaults(defineProps<Props>(), {
  content: '',
  latexExpression: '',
  speed: 1,
  delay: 0,
  autoplay: true,
  loop: false,
  fillDirection: 'left-to-right',
  mathMode: false,
  easing: 'power2.inOut',
  textureEnabled: false,
  textureType: 'clean',
  textureIntensity: 'subtle',
  maskColor: '',
  className: '',
  latexClasses: '',
  customStyles: () => ({}),
})

// Template refs
const containerRef = ref<HTMLElement | null>(null)
const contentRef = ref<HTMLElement | null>(null)
const maskRef = ref<HTMLElement | null>(null)

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

// LaTeX fill animation
const {
  isAnimating,
  startAnimation,
  play,
  pause,
  restart,
} = useLatexFillAnimation(containerRef, {
  speed: props.speed,
  delay: props.delay,
  autoplay: props.autoplay,
  loop: props.loop,
  easing: props.easing,
  fillDirection: props.fillDirection,
  mathMode: props.mathMode,
})

// Computed styles
const containerStyles = computed(() => ({
  position: 'relative' as const,
  display: 'inline-block' as const,
  verticalAlign: 'baseline' as const,
  ...(props.textureEnabled ? textureStyles.value : {}),
  ...props.customStyles,
}))

const contentStyles = computed(() => ({
  position: 'relative' as const,
  zIndex: 2,
}))

const maskStyles = computed(() => {
  const backgroundColor = props.maskColor || 'var(--color-background)'
  
  return {
    position: 'absolute' as const,
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    backgroundColor,
    zIndex: 3,
    pointerEvents: 'none' as const,
  }
})

// Format content for non-math mode
const formattedContent = computed(() => {
  if (props.mathMode) return ''
  
  // Basic HTML formatting
  return props.content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
})

// Watch for content changes
watch(() => [props.content, props.latexExpression], () => {
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
.latex-fill-container {
  overflow: hidden;
}

.latex-content {
  line-height: 1.4;
}

.latex-content.math-mode {
  /* Ensure proper alignment for mathematical expressions */
  display: inline-flex;
  align-items: center;
}

.latex-mask {
  transition: transform 0.1s ease;
}

/* Enhanced styling for mathematical content */
.latex-content :deep(.katex) {
  font-size: inherit;
}

.latex-content :deep(.katex-display) {
  margin: 0;
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .latex-mask {
    display: none !important;
  }
  
  .latex-fill-container {
    /* Show content immediately without animation */
  }
}
</style>