<template>
  <TabsTrigger
    v-bind="props"
    :class="
      cn(
        [
          // Base styles
          'relative z-10 inline-flex items-center justify-center',
          'rounded-lg px-6 py-2',
          'text-sm font-medium whitespace-nowrap',
          
          // Interactive states
          'transition-all duration-200 ease-out',
          'hover:text-foreground',
          'focus-ring',
          
          // Default state
          'text-muted-foreground',
          
          // Active state - matches BouncyToggle active button
          'data-[state=active]:text-primary',
          'data-[state=active]:font-semibold',
          
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
