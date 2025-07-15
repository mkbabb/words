<template>
  <div class="inline-flex items-baseline gap-0">
    <LaTeX
      :expression="'\\mathfrak{F}'"
      :class="
        cn(
          'text-primary font-bold transition-all duration-300 ease-out',
          sizeClass
        )
      "
    />
    <LaTeX
      :expression="`_{\\text{${subscript}}}`"
      :class="
        cn(
          'text-primary transition-all duration-300 ease-out',
          subscriptSizeClass
        )
      "
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { cn } from '@/utils';
import { LaTeX } from '@/components/custom/latex';

interface FancyFProps {
  mode: 'dictionary' | 'thesaurus';
  size?: 'sm' | 'base' | 'lg' | 'xl';
}

const props = withDefaults(defineProps<FancyFProps>(), {
  size: 'base',
});

const subscript = computed(() => (props.mode === 'dictionary' ? 'd' : 't'));

const sizeClass = computed(() => {
  const sizes = {
    sm: 'text-lg',
    base: 'text-2xl',
    lg: 'text-3xl',
    xl: 'text-4xl',
  };
  return sizes[props.size];
});

const subscriptSizeClass = computed(() => {
  const sizes = {
    sm: 'text-xs',
    base: 'text-base',
    lg: 'text-lg',
    xl: 'text-xl',
  };
  return sizes[props.size];
});
</script>
