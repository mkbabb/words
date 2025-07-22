<template>
  <span 
    class="shimmer-text hover-shimmer" 
    :class="[textClass, { 'is-hovered': isHovered }]"
    :style="shimmerStyle"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    {{ text }}
  </span>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'

const isHovered = ref(false)

interface Props {
  text: string
  textClass?: string
  duration?: number
  interval?: number // Time between shimmers in seconds
}

const props = withDefaults(defineProps<Props>(), {
  textClass: 'text-base',
  duration: 1800,
  interval: 15 // Default: shimmer every 15 seconds
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

// Generate shimmer style with randomized interval-based animation
const shimmerStyle = computed(() => {
  // Add randomness to the interval (±40% variation)
  const randomVariation = 0.4;
  const minInterval = props.interval * (1 - randomVariation);
  const maxInterval = props.interval * (1 + randomVariation);
  const randomizedInterval = Math.random() * (maxInterval - minInterval) + minInterval;
  
  const totalCycleDuration = randomizedInterval * 1000; // Convert to milliseconds
  const shimmerDuration = props.duration;
  const randomDelay = Math.random() * randomizedInterval * 200; // Random delay within first 20% of interval
  
  // Faster hover shimmer duration
  const hoverShimmerDuration = Math.max(shimmerDuration * 0.7, 800); // 30% faster, minimum 800ms
  
  return {
    '--shimmer-window-size': `${shimmerWindowSize.value}%`,
    '--shimmer-duration': `${shimmerDuration}ms`,
    '--shimmer-hover-duration': `${hoverShimmerDuration}ms`,
    '--shimmer-cycle-duration': `${totalCycleDuration}ms`,
    '--shimmer-delay': `${randomDelay}ms`
  };
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
  background-size: var(--shimmer-window-size);
  background-position-x: 100%;
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
  animation: 
    shimmer var(--shimmer-duration) ease-in-out,
    shimmer-cycle var(--shimmer-cycle-duration) infinite;
  animation-delay: var(--shimmer-delay);
  
  /* Light mode shimmer colors */
  --shimmer-base: #374151;    /* gray-700 - dark base */
  --shimmer-highlight: #f9fafb; /* gray-50 - bright highlight */
}

/* Dark mode shimmer colors - properly inverted */
:global(.dark) .shimmer-text {
  --shimmer-base: #f9fafb;    /* gray-50 - light base (inverted) */
  --shimmer-highlight: #1f2937; /* gray-800 - dark highlight (inverted) */
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

@keyframes shimmer-cycle {
  0%, 90% {
    opacity: 1;
  }
  95%, 100% {
    opacity: 1;
  }
}

/* Hover-triggered shimmer - override existing animation */
.hover-shimmer.is-hovered {
  animation: shimmer-hover var(--shimmer-hover-duration) ease-in-out !important;
  animation-delay: 0s !important;
}

@keyframes shimmer-hover {
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