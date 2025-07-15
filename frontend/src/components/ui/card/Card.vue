<template>
  <div
    :class="
      cn(
        'bg-card text-card-foreground card-shadow hover:card-shadow-hover rounded-2xl transition-all duration-300',
        className
      )
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

defineProps<CardProps>();
</script>
