<template>
  <div 
    :class="cn(
      'cursor-pointer transition-all duration-300 ease-out flex items-center',
      {
        'gap-1': expanded,
        'justify-center': !expanded,
      },
      className
    )"
    @click="$emit('click')"
  >
    <!-- Fancy F -->
    <LaTeX 
      :expression="'\\mathfrak{F}'"
      :class="cn('text-primary font-bold transition-all duration-300', {
        'text-2xl': expanded,
        'text-xl': !expanded,
      })"
    />
    
    <!-- Rest of "loridify" with Fraunces font -->
    <span 
      v-if="expanded"
      :class="cn(
        'font-serif text-foreground transition-all duration-300 transform',
        {
          'text-xl': expanded,
          'scale-x-0 opacity-0': !expanded,
          'scale-x-100 opacity-100': expanded,
        }
      )"
      style="font-family: 'Fraunces', serif; font-weight: 600;"
    >
      loridify
    </span>
  </div>
</template>

<script setup lang="ts">
import { cn } from '@/utils';
import { LaTeX } from '@/components/custom/latex';

interface FloridifyIconProps {
  expanded?: boolean;
  className?: string;
}

const { expanded = false } = defineProps<FloridifyIconProps>();

defineEmits<{
  click: []
}>();
</script>