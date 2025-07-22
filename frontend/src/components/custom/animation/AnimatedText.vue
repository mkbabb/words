<template>
  <div class="text-center relative">
    <h1
      class="depth-text select-none relative z-10"
      :class="[
        'font-fraunces',
        textClass,
        'text-black dark:text-white'
      ]"
    >
      <span
        v-for="(char, index) in displayChars"
        :key="`${text}-${index}`"
        class="char-animate inline-block"
        :style="{
          animationDelay: `${delay + index * stagger}ms`,
          animationDuration: `${duration}ms`,
        }"
      >
        {{ char === ' ' ? '\u00A0' : char }}
      </span>
    </h1>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

interface Props {
  text: string
  textClass?: string
  delay?: number
  stagger?: number
  duration?: number
}

const props = withDefaults(defineProps<Props>(), {
  textClass: 'text-7xl font-black',
  delay: 500,
  stagger: 150,
  duration: 3000,
})

const displayChars = computed(() => {
  return props.text.split('')
})
</script>

<style scoped>
@keyframes char-animate {
  0%, 60%, 100% {
    transform: translateY(0) scale(1) rotateX(0deg);
  }
  20% {
    transform: translateY(-15px) scale(1.1) rotateX(-5deg);
  }
  40% {
    transform: translateY(-8px) scale(1.05) rotateX(-2deg);
  }
}

.char-animate {
  animation: char-animate ease-in-out infinite;
  transform-origin: center bottom;
}

.depth-text {
  perspective: 1000px;
  transform-style: preserve-3d;
  
  /* Chunky thick 3D effect - white shadows for black text */
  text-shadow:
    /* Sharp, defined depth layers */
    1px 1px 0 rgba(255, 255, 255, 0.9),
    2px 2px 0 rgba(255, 255, 255, 0.8),
    3px 3px 0 rgba(255, 255, 255, 0.7),
    4px 4px 0 rgba(255, 255, 255, 0.6),
    5px 5px 0 rgba(255, 255, 255, 0.5),
    6px 6px 0 rgba(255, 255, 255, 0.4),
    7px 7px 0 rgba(255, 255, 255, 0.3),
    8px 8px 0 rgba(255, 255, 255, 0.2),
    9px 9px 0 rgba(255, 255, 255, 0.15),
    10px 10px 0 rgba(255, 255, 255, 0.1),
    11px 11px 0 rgba(255, 255, 255, 0.08),
    12px 12px 0 rgba(255, 255, 255, 0.05);
    
  transition: all 0.3s ease;
}

.dark .depth-text {
  text-shadow:
    /* Chunky thick black shadows for white text */
    1px 1px 0 rgba(0, 0, 0, 0.9),
    2px 2px 0 rgba(0, 0, 0, 0.8),
    3px 3px 0 rgba(0, 0, 0, 0.7),
    4px 4px 0 rgba(0, 0, 0, 0.6),
    5px 5px 0 rgba(0, 0, 0, 0.5),
    6px 6px 0 rgba(0, 0, 0, 0.4),
    7px 7px 0 rgba(0, 0, 0, 0.3),
    8px 8px 0 rgba(0, 0, 0, 0.2),
    9px 9px 0 rgba(0, 0, 0, 0.15),
    10px 10px 0 rgba(0, 0, 0, 0.1),
    11px 11px 0 rgba(0, 0, 0, 0.08),
    12px 12px 0 rgba(0, 0, 0, 0.05);
}

.font-fraunces {
  font-family: 'Fraunces', serif;
  font-variation-settings: 'wght' 900;
}
</style>