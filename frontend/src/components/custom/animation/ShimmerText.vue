<template>
  <span class="shimmer-text" :class="textClass">
    <span
      v-for="(char, index) in displayChars"
      :key="`${text}-${index}`"
      class="shimmer-char"
      :style="{
        '--char-index': index,
        '--total-chars': displayChars.length,
        animationDelay: `${index * delay}ms`,
        animationDuration: `${duration}ms`
      }"
    >{{ char === ' ' ? '\u00A0' : char }}</span>
  </span>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  text: string
  textClass?: string
  delay?: number
  duration?: number
  shimmerColor?: string
}

const props = withDefaults(defineProps<Props>(), {
  textClass: 'text-base',
  delay: 20,
  duration: 600,
  shimmerColor: 'rgba(59, 130, 246, 0.9)'
})

const displayChars = computed(() => {
  return props.text.split('')
})
</script>

<style scoped>
.shimmer-text {
  display: inline-block;
  position: relative;
}

.shimmer-char {
  display: inline-block;
  position: relative;
  color: inherit;
  animation: shimmer var(--duration, 1500ms) ease-in-out infinite;
}

@keyframes shimmer {
  0% {
    background: linear-gradient(
      90deg,
      transparent 0%,
      transparent 45%,
      v-bind(shimmerColor) 50%,
      transparent 55%,
      transparent 100%
    );
    background-size: 300% 100%;
    background-position: -300% 0;
    background-clip: text;
    -webkit-background-clip: text;
    color: transparent;
  }
  
  50% {
    background-position: 150% 0;
    background-clip: text;
    -webkit-background-clip: text;
    color: transparent;
  }
  
  60% {
    background: none;
    color: inherit;
  }
  
  100% {
    background: none;
    color: inherit;
  }
}

/* Tailwind compatibility - ensure proper shimmer effect */
.shimmer-char:global(.text-white) {
  --shimmer-color: rgba(255, 255, 255, 0.8);
}

.shimmer-char:global(.text-black) {
  --shimmer-color: rgba(0, 0, 0, 0.8);
}

.shimmer-char:global(.text-primary) {
  --shimmer-color: rgb(var(--primary));
}

/* Dark mode compatibility */
:global(.dark) .shimmer-char {
  --shimmer-color: rgba(255, 255, 255, 0.9);
}
</style>