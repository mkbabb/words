<template>
  <TooltipTrigger v-bind="props">
    <slot />
  </TooltipTrigger>
</template>

<script setup lang="ts">
import { TooltipTrigger, type TooltipTriggerProps } from 'reka-ui';

interface Props extends TooltipTriggerProps {}

const props = defineProps<Props>();
</script>