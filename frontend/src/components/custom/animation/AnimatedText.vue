<template>
  <div class="text-center relative">
    <h1
      class="depth-text select-none relative z-10"
      :class="[
        'font-fraunces',
        textClass,
        'text-gray-900 dark:text-gray-100'
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
  
  /* Advanced layered depth effect */
  text-shadow:
    /* Close shadows for definition */
    1px 1px 0 rgba(0, 0, 0, 0.4),
    2px 2px 0 rgba(0, 0, 0, 0.35),
    3px 3px 0 rgba(0, 0, 0, 0.3),
    4px 4px 0 rgba(0, 0, 0, 0.25),
    5px 5px 0 rgba(0, 0, 0, 0.2),
    6px 6px 0 rgba(0, 0, 0, 0.15),
    7px 7px 0 rgba(0, 0, 0, 0.1),
    8px 8px 0 rgba(0, 0, 0, 0.08),
    
    /* Atmospheric depth */
    10px 10px 8px rgba(0, 0, 0, 0.3),
    15px 15px 20px rgba(0, 0, 0, 0.2),
    20px 20px 30px rgba(0, 0, 0, 0.15),
    
    /* Dramatic glow */
    0 0 40px rgba(0, 0, 0, 0.1),
    0 0 80px rgba(0, 0, 0, 0.05);
    
  transition: all 0.3s ease;
}

.dark .depth-text {
  text-shadow:
    /* Softer shadows for dark mode */
    1px 1px 0 rgba(255, 255, 255, 0.2),
    2px 2px 0 rgba(255, 255, 255, 0.18),
    3px 3px 0 rgba(255, 255, 255, 0.16),
    4px 4px 0 rgba(255, 255, 255, 0.14),
    5px 5px 0 rgba(255, 255, 255, 0.12),
    6px 6px 0 rgba(255, 255, 255, 0.1),
    7px 7px 0 rgba(255, 255, 255, 0.08),
    8px 8px 0 rgba(255, 255, 255, 0.06),
    
    /* Atmospheric depth */
    10px 10px 8px rgba(255, 255, 255, 0.15),
    15px 15px 20px rgba(255, 255, 255, 0.1),
    20px 20px 30px rgba(255, 255, 255, 0.08),
    
    /* Subtle glow */
    0 0 40px rgba(255, 255, 255, 0.05),
    0 0 80px rgba(255, 255, 255, 0.03);
}

.font-fraunces {
  font-family: 'Fraunces', serif;
  font-variation-settings: 'wght' 900;
}
</style>