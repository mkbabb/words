<template>
  <div
    ref="containerRef"
    :class="[
      'three-b1b-container',
      className
    ]"
    :style="containerStyles"
  >
    <!-- Content with optional term wrapping for equation reveals -->
    <div
      ref="contentRef"
      :class="[
        'three-b1b-content',
        { 'equation-mode': fillStyle === 'equation-reveal' }
      ]"
    >
      <!-- LaTeX component integration for math mode -->
      <LaTeX
        v-if="mathMode && latexExpression"
        :expression="latexExpression"
        :class="latexClasses"
      />
      <!-- Regular content with term wrapping -->
      <template v-else-if="fillStyle === 'equation-reveal' && terms.length > 0">
        <span
          v-for="(term, index) in terms"
          :key="index"
          :class="[
            'equation-term',
            { 'highlight': highlightTerms.includes(index) }
          ]"
        >
          {{ term }}
        </span>
      </template>
      <!-- Simple content -->
      <span v-else v-html="formattedContent" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { use3b1bAnimation } from '@/composables/use3b1bAnimations'
import { LaTeX } from '@/components/custom/latex'
import type { ThreeB1BAnimationOptions } from '@/composables/use3b1bAnimations'

interface Props {
  /** Content to animate (text or LaTeX expression) */
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
  /** 3b1b-style fill animation type */
  fillStyle?: ThreeB1BAnimationOptions['fillStyle']
  /** Enable math mode (uses LaTeX component) */
  mathMode?: boolean
  /** Easing function */
  easing?: string
  /** Terms to animate separately (for equation-reveal) */
  terms?: string[]
  /** Indices of terms to highlight */
  highlightTerms?: number[]
  /** Enable color highlights */
  colorHighlights?: boolean
  /** Stagger delay for multi-element animations */
  stagger?: number
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
  speed: 1.5,
  delay: 0,
  autoplay: true,
  loop: false,
  fillStyle: '3b1b-radial',
  mathMode: false,
  easing: 'power3.inOut',
  terms: () => [],
  highlightTerms: () => [],
  colorHighlights: false,
  stagger: 0.05,
  className: '',
  latexClasses: '',
  customStyles: () => ({}),
})

// Template refs
const containerRef = ref<HTMLElement | null>(null)
const contentRef = ref<HTMLElement | null>(null)

// 3b1b animation
const {
  isAnimating,
  startAnimation,
  play,
  pause,
  restart,
} = use3b1bAnimation(containerRef, {
  speed: props.speed,
  delay: props.delay,
  autoplay: props.autoplay,
  loop: props.loop,
  easing: props.easing,
  fillStyle: props.fillStyle,
  colorHighlights: props.colorHighlights,
  stagger: props.stagger,
})

// Computed styles
const containerStyles = computed(() => ({
  position: 'relative' as const,
  display: 'inline-block' as const,
  verticalAlign: 'baseline' as const,
  ...props.customStyles,
}))

// Format content for non-math mode
const formattedContent = computed(() => {
  if (props.mathMode || props.terms.length > 0) return ''
  
  // Basic HTML formatting
  return props.content
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
})

// Watch for content changes
watch(() => [props.content, props.latexExpression, props.terms], () => {
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
.three-b1b-container {
  overflow: visible; /* Allow effects to extend beyond bounds */
}

.three-b1b-content {
  line-height: 1.4;
  position: relative;
}

/* Equation mode styling */
.three-b1b-content.equation-mode {
  display: inline-flex;
  align-items: center;
  gap: 0.3em;
}

.equation-term {
  display: inline-block;
  transition: all 0.3s ease;
}

/* Highlight styling for terms */
.equation-term.highlight {
  position: relative;
  z-index: 1;
}

/* Mathematical content styling */
.three-b1b-content :deep(.katex) {
  font-size: inherit;
}

.three-b1b-content :deep(.katex-display) {
  margin: 0;
}

/* 3b1b color palette */
.three-b1b-content :deep(.blue) {
  color: #3b82f6;
}

.three-b1b-content :deep(.yellow) {
  color: #fbbf24;
}

.three-b1b-content :deep(.green) {
  color: #10b981;
}

.three-b1b-content :deep(.red) {
  color: #ef4444;
}

.three-b1b-content :deep(.purple) {
  color: #8b5cf6;
}

/* Enhanced visual effects */
.three-b1b-container::before {
  content: '';
  position: absolute;
  inset: -10px;
  background: radial-gradient(
    circle at 50% 50%,
    rgba(59, 130, 246, 0.1) 0%,
    transparent 70%
  );
  opacity: 0;
  transition: opacity 0.5s ease;
  pointer-events: none;
  z-index: -1;
}

.three-b1b-container:hover::before {
  opacity: 1;
}

/* Reduced motion support */
@media (prefers-reduced-motion: reduce) {
  .three-b1b-container {
    clip-path: none !important;
  }
  
  .equation-term {
    opacity: 1 !important;
    transform: none !important;
  }
}
</style>