<template>
  <span class="shimmer-text" :class="textClass">
    {{ text }}
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  text: string
  textClass?: string
  duration?: number
}

const props = withDefaults(defineProps<Props>(), {
  textClass: 'text-base',
  duration: 1800
})

// Calculate shimmer window size based on text length and estimated size
const shimmerWindowSize = computed(() => {
  const textLength = props.text.length
  const hasLargeText = props.textClass?.includes('text-xl') || 
                      props.textClass?.includes('text-2xl') ||
                      props.textClass?.includes('text-3xl') ||
                      props.textClass?.includes('text-4xl') ||
                      props.textClass?.includes('text-5xl') ||
                      props.textClass?.includes('text-6xl') ||
                      props.textClass?.includes('text-7xl') ||
                      props.textClass?.includes('text-8xl')
  
  // Base window size, adjusted for text size and length
  let baseSize = 300
  
  // Larger text gets a bigger shimmer window
  if (hasLargeText) {
    baseSize = 400
  }
  
  // Longer text gets a slightly bigger window for smoother effect
  if (textLength > 50) {
    baseSize += 50
  } else if (textLength > 100) {
    baseSize += 100
  }
  
  return baseSize
})
</script>

<style scoped>
.shimmer-text {
  background: linear-gradient(
    -45deg,
    var(--shimmer-base) 35%,
    var(--shimmer-highlight) 50%,
    var(--shimmer-base) 65%
  );
  background-size: v-bind('shimmerWindowSize + "%"');
  background-position-x: 100%;
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
  animation: shimmer v-bind('props.duration + "ms"') ease-in-out infinite;
  animation-delay: v-bind('Math.random() * 200 + "ms"');
  
  /* Enhanced visibility shimmer colors for light mode */
  --shimmer-base: #1f2937;    /* gray-800 - dark base */
  --shimmer-highlight: #e5e7eb; /* gray-200 - much lighter highlight */
}

/* Dark mode shimmer colors - lighter for contrast */
:global(.dark) .shimmer-text {
  --shimmer-base: #f9fafb;    /* gray-50 - very light base */
  --shimmer-highlight: #6b7280; /* gray-500 - much darker highlight */
}

@keyframes shimmer {
  0% {
    background-position-x: 100%;
  }
  15% {
    background-position-x: 85%;
  }
  85% {
    background-position-x: 15%;
  }
  100% {
    background-position-x: 0%;
  }
}
</style>