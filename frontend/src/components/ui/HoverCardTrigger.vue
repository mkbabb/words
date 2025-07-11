<template>
  <HoverCardTrigger :as-child="asChild">
    <slot />
  </HoverCardTrigger>
</template>

<script setup lang="ts">
import { HoverCardTrigger } from 'radix-vue'

interface Props {
  asChild?: boolean
}

withDefaults(defineProps<Props>(), {
  asChild: false
})
</script>