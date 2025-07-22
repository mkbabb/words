<template>
  <span 
    :class="[
      'shimmer-text',
      textClass,
      { 'is-hovered': isHovered }
    ]"
    :style="shimmerStyles"
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
  gradientFrom?: string
  gradientTo?: string
  textColor?: string
}

const props = withDefaults(defineProps<Props>(), {
  textClass: 'text-base',
  duration: 1800,
  interval: 15,
  gradientFrom: '', // Will use CSS custom properties
  gradientTo: '',   // Will use CSS custom properties
  textColor: ''     // Will use CSS custom properties
})

const shimmerStyles = computed(() => {
  // Add randomness to the interval (±40% variation)
  const randomVariation = 0.4;
  const minInterval = props.interval * (1 - randomVariation);
  const maxInterval = props.interval * (1 + randomVariation);
  const randomizedInterval = Math.random() * (maxInterval - minInterval) + minInterval;
  
  const totalCycleDuration = randomizedInterval * 1000;
  const randomDelay = Math.random() * randomizedInterval * 200;
  const hoverDuration = Math.max(props.duration * 0.7, 800);

  return {
    '--shimmer-duration': `${props.duration}ms`,
    '--shimmer-hover-duration': `${hoverDuration}ms`,
    '--shimmer-cycle-duration': `${totalCycleDuration}ms`,
    '--shimmer-delay': `${randomDelay}ms`,
    '--gradient-from': props.gradientFrom,
    '--gradient-to': props.gradientTo,
    '--text-color': props.textColor,
  };
})
</script>

<style scoped>
.shimmer-text {
  /* Default colors */
  --text-color: hsl(var(--foreground));
  
  /* Set normal text color */
  color: var(--text-color);
  position: relative;
  overflow: hidden;
  
  /* Animation setup */
  animation: shimmer-cycle var(--shimmer-cycle-duration) infinite;
  animation-delay: var(--shimmer-delay);
}

.shimmer-text::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.6) 50%,
    transparent 100%
  );
  transform: translateX(-100%);
  opacity: 0;
  pointer-events: none;
}

/* Dark mode shimmer - dark gradient for white text */
:global(.dark) .shimmer-text::after {
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(0, 0, 0, 0.4) 50%,
    transparent 100%
  );
}

@keyframes shimmer-cycle {
  0%, 90% {
    /* Do nothing most of the time */
  }
  91% {
    /* Start shimmer */
  }
  91%, 99% {
    /* Shimmer duration */
  }
  100% {
    /* End shimmer */
  }
}

.shimmer-text::after {
  animation: shimmer-sweep var(--shimmer-duration) ease-in-out;
  animation-delay: calc(var(--shimmer-delay) + var(--shimmer-cycle-duration) * 0.9);
}

@keyframes shimmer-sweep {
  0% {
    transform: translateX(-100%);
    opacity: 0;
  }
  20% {
    opacity: 1;
  }
  80% {
    opacity: 1;
  }
  100% {
    transform: translateX(100%);
    opacity: 0;
  }
}

/* Hover shimmer - immediate */
.shimmer-text.is-hovered::after {
  animation: shimmer-hover var(--shimmer-hover-duration) ease-in-out !important;
  animation-delay: 0s !important;
}

@keyframes shimmer-hover {
  0% {
    transform: translateX(-100%);
    opacity: 0;
  }
  20% {
    opacity: 1;
  }
  80% {
    opacity: 1;
  }
  100% {
    transform: translateX(100%);
    opacity: 0;
  }
}

/* Respect reduced motion */
@media (prefers-reduced-motion: reduce) {
  .shimmer-text,
  .shimmer-text::after {
    animation: none !important;
  }
}
</style>