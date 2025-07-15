<template>
  <TabsTrigger
    v-bind="props"
    :class="
      cn(
        [
          // Base styles
          'inline-flex items-center justify-center',
          'rounded-sm px-3 py-1.5',
          'text-sm font-medium whitespace-nowrap',
          
          // Interactive states
          'transition-smooth hover-lift-sm',
          'hover:bg-muted/80',
          'focus-ring',
          
          // Active state
          'data-[state=active]:bg-background',
          'data-[state=active]:text-foreground',
          'data-[state=active]:shadow-sm',
          'data-[state=active]:hover:scale-100',
          
          // Disabled state
          'disabled:pointer-events-none disabled:opacity-50',
        ].join(' '),
        props.class
      )
    "
  >
    <slot />
  </TabsTrigger>
</template>

<script setup lang="ts">
import { type HTMLAttributes } from 'vue';
import { TabsTrigger, type TabsTriggerProps } from 'radix-vue';
import { cn } from '@/utils';

const props = defineProps<
  TabsTriggerProps & { class?: HTMLAttributes['class'] }
>();
</script>
