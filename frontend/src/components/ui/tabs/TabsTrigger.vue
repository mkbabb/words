<template>
  <TabsTrigger
    v-bind="props"
    :class="
      cn(
        'ring-offset-background focus-visible:ring-ring data-[state=active]:bg-background data-[state=active]:text-foreground hover:bg-muted/80 inline-flex items-center justify-center rounded-sm px-3 py-1.5 text-sm font-medium whitespace-nowrap transition-all focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 data-[state=active]:shadow-sm',
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
