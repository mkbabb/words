<template>
  <TooltipProvider v-bind="props">
    <slot />
  </TooltipProvider>
</template>

<script setup lang="ts">
import { TooltipProvider, type TooltipProviderProps } from 'reka-ui';

interface Props extends TooltipProviderProps {}

const props = withDefaults(defineProps<Props>(), {
  delayDuration: 0,
});
</script>