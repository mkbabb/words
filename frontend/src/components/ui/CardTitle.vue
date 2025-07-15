<template>
  <h3 :class="cn('leading-none font-semibold tracking-tight', className)">
    <slot />
  </h3>
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface CardTitleProps {
  className?: string;
}

const props = withDefaults(defineProps<CardTitleProps>(), {
  className: '',
});

const { className } = props;
</script>
