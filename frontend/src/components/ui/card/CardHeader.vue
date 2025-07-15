<template>
  <div :class="cn('flex flex-col space-y-1.5 p-6', className)">
    <slot />
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface CardHeaderProps {
  className?: string;
}

defineProps<CardHeaderProps>();
</script>
