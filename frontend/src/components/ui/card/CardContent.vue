<template>
  <div :class="cn('p-6 pt-0', className)">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface CardContentProps {
  className?: string;
}

defineProps<CardContentProps>();
</script>
