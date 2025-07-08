<template>
  <div :class="cn('rounded-xl border bg-card text-card-foreground shadow', className)">
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