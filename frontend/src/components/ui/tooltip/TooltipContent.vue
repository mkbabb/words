<template>
  <TooltipPortal>
    <TooltipContent
      v-bind="{ ...props, sideOffset: sideOffset ?? 4 }"
      :class="cn(
        'z-50 overflow-hidden rounded-md bg-primary px-3 py-1.5 text-xs text-primary-foreground animate-in fade-in-0 zoom-in-95 data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=closed]:zoom-out-95 data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2',
        className
      )"
    >
      <slot />
    </TooltipContent>
  </TooltipPortal>
</template>

<script setup lang="ts">
import { TooltipContent, TooltipPortal, type TooltipContentProps } from 'reka-ui';
import { cn } from '@/utils';

interface Props extends TooltipContentProps {
  className?: string;
  sideOffset?: number;
}

const props = defineProps<Props>();
</script>