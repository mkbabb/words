<template>
  <div
    :class="
      cn(
        'flex cursor-pointer items-center transition-all duration-300 ease-out',
        {
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
      :show-subscript="showSubscript"
      class="transition-all duration-300"
      @toggle-mode="$emit('toggle-mode')"
    />

    <!-- Rest of "loridify" with Fraunces font -->
    <span
      v-if="expanded"
      :class="
        cn('text-foreground font-serif text-xl transition-all duration-300', {
          'scale-x-0 opacity-0': !expanded,
          'scale-x-100 opacity-100': expanded,
        })
      "
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
  showSubscript?: boolean;
}

const { expanded = false, mode = 'dictionary', clickable = false, showSubscript = true } = defineProps<FloridifyIconProps>();

defineEmits<{
  click: [];
  'toggle-mode': [];
}>();
</script>