<template>
  <div
    :class="
      cn(
        'flex cursor-pointer items-center transition-all duration-300 ease-out',
        {
          'gap-1': expanded,
          'justify-center': !expanded,
        },
        className
      )
    "
    @click="$emit('click')"
  >
    <!-- Fancy F using reusable component -->
    <FancyF 
      mode="dictionary" 
      :size="expanded ? 'lg' : 'base'"
      class="transition-all duration-300"
    />

    <!-- Rest of "loridify" with Fraunces font -->
    <span
      v-if="expanded"
      :class="
        cn('text-foreground transform font-serif transition-all duration-300', {
          'text-xl': expanded,
          'scale-x-0 opacity-0': !expanded,
          'scale-x-100 opacity-100': expanded,
        })
      "
      style="font-family: 'Fraunces', serif; font-weight: 600"
    >
      loridify
    </span>
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/utils';
import FancyF from './FancyF.vue';

interface FloridifyIconProps {
  expanded?: boolean;
  className?: string;
}

const { expanded = false } = defineProps<FloridifyIconProps>();

defineEmits<{
  click: [];
}>();
</script>