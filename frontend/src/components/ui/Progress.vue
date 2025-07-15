<template>
  <div
    :class="
      cn(
        'bg-secondary relative h-4 w-full overflow-hidden rounded-full',
        props.class
      )
    "
  >
    <div
      class="bg-primary h-full w-full flex-1 transition-all"
      :style="{ transform: `translateX(-${100 - (value || 0)}%)` }"
    />
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface Props {
  value?: number;
  class?: any;
}

const props = defineProps<Props>();
</script>
