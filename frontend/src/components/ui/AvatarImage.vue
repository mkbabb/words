<template>
  <AvatarImage :class="cn('aspect-square h-full w-full', $attrs.class as string)" :src="src">
    <slot />
  </AvatarImage>
</template>

<script setup lang="ts">
import { AvatarImage } from 'radix-vue'
import { cn } from '@/utils'

interface Props {
  src: string
}

defineProps<Props>()
</script>