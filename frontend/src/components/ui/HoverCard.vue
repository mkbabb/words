<template>
  <HoverCardRoot :open-delay="openDelay" :close-delay="closeDelay">
    <slot />
  </HoverCardRoot>
</template>

<script setup lang="ts">
import { HoverCardRoot } from 'radix-vue'

interface Props {
  openDelay?: number
  closeDelay?: number
}

withDefaults(defineProps<Props>(), {
  openDelay: 700,
  closeDelay: 300
})
</script>