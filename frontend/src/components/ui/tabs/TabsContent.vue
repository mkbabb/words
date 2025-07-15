<template>
  <TabsContent
    v-bind="props"
    :class="
      cn(
        'ring-offset-background focus-visible:ring-ring mt-2 focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:outline-none',
        props.class
      )
    "
  >
    <slot />
  </TabsContent>
</template>

<script setup lang="ts">
import { type HTMLAttributes } from 'vue';
import { TabsContent, type TabsContentProps } from 'radix-vue';
import { cn } from '@/utils';

const props = defineProps<
  TabsContentProps & { class?: HTMLAttributes['class'] }
>();
</script>
