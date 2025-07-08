<template>
  <div 
    :class="cn(
      'animate-pulse rounded-xl bg-muted',
      className
    )"
  />
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface SkeletonProps {
  className?: string;
}

defineProps<SkeletonProps>();
</script>