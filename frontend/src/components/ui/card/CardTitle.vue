<template>
  <h3 :class="cn('text-lg sm:text-xl font-semibold tracking-tight leading-none', className)">
    <slot />
  </h3>
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface CardTitleProps {
  className?: string;
}

defineProps<CardTitleProps>();
</script>
