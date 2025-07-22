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
      <template v-for="(char, index) in currentText" :key="index">
        <span
          v-if="char !== '\n'"
          class="lift-down inline-block"
          :style="{
            animationDelay: `${index * offset}s`,
            animationDuration: duration,
          }"
        >{{ char === ' ' ? '\u00A0' : char }}</span>
        <br v-else class="w-full" />
      </template>
      
      <!-- Animated dots -->
      <span v-if="showDots" class="dots ml-1">
        <span 
          v-for="i in 3" 
          :key="i"
          class="dot-fade inline-block"
          :style="{ 
            animationDelay: `${(i - 1) * 0.2}s`,
            animationDuration: '1.5s'
          }"
        >.</span>
      </span>
    </h1>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useWindowSize } from '@vueuse/core'

const HTML_SPACE = '\u00a0'
const { width } = useWindowSize()

interface Props {
  text: string
  textClass?: string
  offset?: number
  showDots?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  textClass: 'text-7xl font-black',
  offset: 0.2,
  showDots: false,
})

const newText = computed(() => props.text.replace(/ /g, HTML_SPACE))
const brokenText = computed(() => newText.value.replace(/\s/g, HTML_SPACE + '\n'))

const currentText = computed(() => {
  return width.value < 768 ? brokenText.value : newText.value
})

const duration = computed(() => `${currentText.value.length * props.offset + props.offset * 10}s`)
</script>

<style scoped>
.lift-down {
  animation: liftDown 3s ease-in-out infinite;
  animation-fill-mode: forwards;
  transform-origin: center bottom;
}

@keyframes liftDown {
  0% {
    transform: translateY(0);
  }
  5% {
    transform: translateY(-10px);
  }
  10% {
    transform: translateY(0);
  }
  100% {
    transform: translateY(0);
  }
}

.dot-fade {
  animation: dotFade 1.5s ease-in-out infinite;
  animation-fill-mode: forwards;
}

@keyframes dotFade {
  0%,
  100% {
    opacity: 0;
  }
  50% {
    opacity: 1;
  }
}

.depth-text {
  perspective: 1000px;
  transform-style: preserve-3d;
  
  /* Chunky stark 3D effect - off-white shadows for better background compatibility */
  text-shadow:
    /* Sharp, defined depth layers with subtle off-white tone */
    1px 1px 0 rgba(248, 248, 248, 1),
    2px 2px 0 rgba(248, 248, 248, 0.95),
    3px 3px 0 rgba(248, 248, 248, 0.9),
    4px 4px 0 rgba(248, 248, 248, 0.85),
    5px 5px 0 rgba(248, 248, 248, 0.8),
    6px 6px 0 rgba(248, 248, 248, 0.75),
    7px 7px 0 rgba(248, 248, 248, 0.7),
    8px 8px 0 rgba(248, 248, 248, 0.65);
    
  transition: all 0.3s ease;
}

.dark .depth-text {
  text-shadow:
    /* Chunky stark off-black shadows for better background compatibility */
    1px 1px 0 rgba(32, 32, 32, 1),
    2px 2px 0 rgba(32, 32, 32, 0.95),
    3px 3px 0 rgba(32, 32, 32, 0.9),
    4px 4px 0 rgba(32, 32, 32, 0.85),
    5px 5px 0 rgba(32, 32, 32, 0.8),
    6px 6px 0 rgba(32, 32, 32, 0.75),
    7px 7px 0 rgba(32, 32, 32, 0.7),
    8px 8px 0 rgba(32, 32, 32, 0.65);
}

.font-fraunces {
  font-family: 'Fraunces', serif;
  font-variation-settings: 'wght' 900;
}
</style>