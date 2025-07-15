<template>
  <TabsContent
    v-bind="props"
    :class="
      cn(
        'mt-2 focus-ring animate-in fade-in-50 duration-300',
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
