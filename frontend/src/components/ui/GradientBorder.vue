<template>
  <div
    :class="
      cn(
        'relative rounded-xl bg-gradient-to-r p-[1px]',
        gradientClasses,
        props.class
      )
    "
  >
    <div :class="cn('bg-background relative rounded-xl', contentClass)">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { cn } from '@/utils';

interface Props {
  variant?: 'default' | 'rainbow' | 'primary' | 'accent';
  class?: any;
  contentClass?: any;
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
});

const gradientClasses = computed(() => {
  switch (props.variant) {
    case 'rainbow':
      return 'from-red-500 via-yellow-500 via-green-500 via-blue-500 to-purple-500';
    case 'primary':
      return 'from-primary/50 via-primary to-primary/50';
    case 'accent':
      return 'from-accent/50 via-accent to-accent/50';
    default:
      return 'from-border via-muted to-border';
  }
});
</script>
