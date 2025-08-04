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
      :mode="mode" 
      :size="expanded ? 'lg' : 'base'"
      :clickable="clickable"
      class="transition-all duration-300"
      @toggle-mode="$emit('toggle-mode')"
    />

    <!-- Rest of "loridify" with Fraunces font -->
    <span
      v-if="expanded"
      :class="
        cn('text-foreground transform font-serif transition-all duration-300 -m-1', {
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
import type { LookupMode } from '@/types';

interface FloridifyIconProps {
  expanded?: boolean;
  className?: string;
  mode?: LookupMode;
  clickable?: boolean;
}

const { expanded = false, mode = 'dictionary', clickable = false } = defineProps<FloridifyIconProps>();

defineEmits<{
  click: [];
  'toggle-mode': [];
}>();
</script>