<template>
  <div
    :class="
      cn('bg-card text-card-foreground rounded-xl border shadow', className)
    "
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface CardProps {
  className?: string;
}

const props = withDefaults(defineProps<CardProps>(), {
  className: '',
});

const { className } = props;
</script>
