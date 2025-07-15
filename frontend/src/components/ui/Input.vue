<template>
  <input
    :class="
      cn(
        'border-input bg-background placeholder:text-muted-foreground focus-visible:ring-ring flex h-9 w-full rounded-xl border-2 px-3 py-1 text-sm shadow-sm transition-all duration-200 file:border-0 file:bg-transparent file:text-sm file:font-medium focus-visible:ring-2 focus-visible:outline-none disabled:cursor-not-allowed disabled:opacity-50',
        className
      )
    "
    v-bind="$attrs"
  />
</template>

<script setup lang="ts">
import { cn } from '@/utils';

interface InputProps {
  className?: string;
}

const props = withDefaults(defineProps<InputProps>(), {
  className: '',
});

const { className } = props;
</script>
