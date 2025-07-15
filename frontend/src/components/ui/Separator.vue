<template>
  <div
    role="separator"
    :class="
      cn(
        'bg-border shrink-0',
        orientation === 'horizontal' ? 'h-[1px] w-full' : 'h-full w-[1px]',
        className
      )
    "
  />
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface SeparatorProps {
  orientation?: 'horizontal' | 'vertical';
  className?: string;
}

defineProps<SeparatorProps>();
</script>
