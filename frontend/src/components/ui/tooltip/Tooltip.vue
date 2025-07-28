<template>
  <TooltipProvider>
    <TooltipRoot v-bind="props">
      <slot />
    </TooltipRoot>
  </TooltipProvider>
</template>

<script setup lang="ts">
import { TooltipProvider, TooltipRoot, type TooltipRootProps } from 'reka-ui';

interface TooltipProps extends TooltipRootProps {}

const props = defineProps<TooltipProps>();
</script>