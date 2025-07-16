<template>
  <div class="inline-flex items-baseline gap-0 hover-lift">
    <LaTeX
      :expression="'\\mathfrak{F}'"
      :class="[
        'text-primary font-bold',
        {
          'text-lg': size === 'sm',
          'text-2xl': size === 'base',
          'text-3xl': size === 'lg',
          'text-4xl': size === 'xl'
        }
      ]"
    />
    <LaTeX
      :expression="`_{\\text{${mode === 'dictionary' ? 'd' : 't'}}}`"
      :class="[
        'text-primary',
        {
          'text-xs': size === 'sm',
          'text-base': size === 'base',
          'text-lg': size === 'lg',
          'text-xl': size === 'xl'
        }
      ]"
    />
  </div>
</template>

<script setup lang="ts">
import { LaTeX } from '@/components/custom/latex';

interface FancyFProps {
  mode: 'dictionary' | 'thesaurus';
  size?: 'sm' | 'base' | 'lg' | 'xl';
}

withDefaults(defineProps<FancyFProps>(), {
  size: 'base',
});
</script>
