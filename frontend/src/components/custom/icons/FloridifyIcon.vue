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
      :class="cn('transition-all duration-300', {
        '-translate-y-px': expanded,
        '-translate-x-1': expanded && showSubscript,
        'translate-x-0.5': expanded && !showSubscript,
      })"
      @toggle-mode="$emit('toggle-mode')"
    />

    <!-- Rest of "loridify" with Fraunces font -->
    <span
      v-if="expanded"
      :class="
        cn('text-foreground transform font-serif transition-all duration-300', {
          'text-xl': expanded,
          'scale-x-0 opacity-0': !expanded,
          'scale-x-100 opacity-100': expanded,
          '-ml-1.5': showSubscript,
          '-ml-0.5': !showSubscript,
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