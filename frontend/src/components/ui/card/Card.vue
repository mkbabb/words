<template>
  <div :class="cn('rounded-2xl bg-card text-card-foreground card-shadow transition-all duration-300 hover:card-shadow-hover', className)">
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