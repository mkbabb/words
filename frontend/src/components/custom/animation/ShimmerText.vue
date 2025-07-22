<template>
  <span :class="textClass">
    {{ text }}
  </span>
</template>

<script setup lang="ts">
interface Props {
  text: string
  textClass?: string
  duration?: number
  interval?: number
  delay?: number
}

withDefaults(defineProps<Props>(), {
  textClass: '',
  duration: 1000,
  interval: 5000,
  delay: 0
})

// Shimmer functionality commented out for now
// Will reimplement later
</script>

<style scoped>
/* Shimmer styles commented out for now */
</style>