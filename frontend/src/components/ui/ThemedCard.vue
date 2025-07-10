<template>
  <div 
    :class="cn(
      'rounded-2xl text-card-foreground transition-all duration-300 relative overflow-hidden',
      themeClasses,
      className
    )"
  >
    <!-- Star Icon for Special Variants -->
    <div 
      v-if="variant !== 'default'" 
      class="absolute top-4 right-4 z-10"
    >
      <StarIcon :variant="variant" />
    </div>
    
    <!-- Sparkle Animation Overlay -->
    <div 
      v-if="variant !== 'default'" 
      :class="cn('absolute inset-0 pointer-events-none', sparkleClasses)"
    />
    
    <!-- Content -->
    <div class="relative z-20">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { cn } from '@/utils';
import StarIcon from './StarIcon.vue';

type CardVariant = 'default' | 'gold' | 'silver' | 'bronze';

interface ThemedCardProps {
  variant?: CardVariant;
  className?: string;
}

const props = withDefaults(defineProps<ThemedCardProps>(), {
  variant: 'default'
});

const themeClasses = computed(() => {
  const baseClasses = 'card-shadow transition-all duration-300';
  
  switch (props.variant) {
    case 'gold':
      return `${baseClasses} card-gold`;
    case 'silver':
      return `${baseClasses} card-silver`;
    case 'bronze':
      return `${baseClasses} card-bronze`;
    default:
      return `${baseClasses} bg-card hover:card-shadow-hover`;
  }
});

const sparkleClasses = computed(() => {
  switch (props.variant) {
    case 'gold':
      return 'sparkle-gold';
    case 'silver':
      return 'sparkle-silver';
    case 'bronze':
      return 'sparkle-bronze';
    default:
      return '';
  }
});
</script>