<template>
  <label
    :class="
      cn(
        'text-sm leading-none font-medium peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
        props.class
      )
    "
    v-bind="props"
  >
    <slot />
  </label>
</template>

<script setup lang="ts">
import { type HTMLAttributes } from 'vue';
import { cn } from '@/utils';

const props = defineProps<{
  class?: HTMLAttributes['class'];
}>();
</script>
