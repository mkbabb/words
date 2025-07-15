<template>
  <TabsRoot v-bind="forwardedProps">
    <slot />
  </TabsRoot>
</template>

<script setup lang="ts">
import { TabsRoot, type TabsRootEmits, type TabsRootProps } from 'radix-vue';
import { useForwardPropsEmits } from 'radix-vue';

const props = defineProps<TabsRootProps>();
const emits = defineEmits<TabsRootEmits>();

const forwardedProps = useForwardPropsEmits(props, emits);
</script>
