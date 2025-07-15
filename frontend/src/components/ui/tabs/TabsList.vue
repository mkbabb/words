<template>
  <TabsList
    v-bind="props"
    :class="
      cn(
        'bg-muted text-muted-foreground inline-flex h-10 items-center justify-center gap-1 rounded-md p-1',
        props.class
      )
    "
  >
    <slot />
  </TabsList>
</template>

<script setup lang="ts">
import { type HTMLAttributes } from 'vue';
import { TabsList, type TabsListProps } from 'radix-vue';
import { cn } from '@/utils';

const props = defineProps<
  TabsListProps & { class?: HTMLAttributes['class'] }
>();
</script>
