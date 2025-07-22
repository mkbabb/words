<template>
  <span 
    class="shimmer-text" 
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
  interval?: number
}

const props = withDefaults(defineProps<Props>(), {
  textClass: 'text-base',
  duration: 1800,
  interval: 15
})

const shimmerStyle = computed(() => {
  const randomVariation = 0.4;
  const minInterval = props.interval * (1 - randomVariation);
  const maxInterval = props.interval * (1 + randomVariation);
  const randomizedInterval = Math.random() * (maxInterval - minInterval) + minInterval;
  
  const totalCycleDuration = randomizedInterval * 1000;
  const shimmerDuration = props.duration;
  const randomDelay = Math.random() * randomizedInterval * 200;
  const hoverShimmerDuration = Math.max(shimmerDuration * 0.7, 800);
  
  return {
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
  background-size: 200%;
  background-position-x: 100%;
  background-clip: text;
  -webkit-background-clip: text;
  color: transparent;
  animation: 
    shimmer var(--shimmer-duration) ease-in-out,
    shimmer-cycle var(--shimmer-cycle-duration) infinite;
  animation-delay: var(--shimmer-delay);
  
  /* Light mode colors - use design system */
  --shimmer-base: hsl(var(--muted-foreground));
  --shimmer-highlight: hsl(var(--primary-foreground) / 0.9);
}

/* Dark mode - highlight should still be lighter than base */
:global(.dark) .shimmer-text {
  --shimmer-base: hsl(var(--muted-foreground));
  --shimmer-highlight: hsl(var(--primary-foreground) / 0.95);
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

.shimmer-text.is-hovered {
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

@media (prefers-reduced-motion: reduce) {
  .shimmer-text {
    animation: none !important;
    color: hsl(var(--foreground)) !important;
    background: none !important;
  }
}
</style>