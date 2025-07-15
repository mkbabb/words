<template>
  <div :class="cn('bg-muted animate-pulse rounded-xl', className)" />
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface SkeletonProps {
  className?: string;
}

defineProps<SkeletonProps>();
</script>
