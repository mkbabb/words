<template>
    <div
        :class="[
            'themed-card themed-shadow-lg flex flex-col gap-6 rounded-xl border bg-card py-6 text-card-foreground relative',
            className,
        ]"
        :data-theme="variant || 'default'"
    >
          <!-- Star Icon - absolute positioned but inside card -->
          <StarIcon 
            v-if="variant && variant !== 'default'"
            :variant="variant" 
            class="absolute top-2 right-2 z-30"
          />

          <!-- Sparkle Animation Overlay -->
          <div 
            v-if="variant && variant !== 'default'" 
            class="themed-sparkle absolute inset-0 pointer-events-none w-full h-full" 
            :style="sparkleStyle"
          />

        <!-- Content -->
        <slot />
    </div>
</template>

<script setup lang="ts">
import { toRefs, computed } from 'vue';
import { StarIcon } from '@/components/custom/icons';

type CardVariant = 'default' | 'gold' | 'silver' | 'bronze';

interface ThemedCardProps {
    variant?: CardVariant;
    className?: string;
}

const props = defineProps<ThemedCardProps>();

// Clean prop handling
const { variant, className } = toRefs(props);

// Generate random variations for sparkle animation and gradient patterns
const sparkleStyle = computed(() => {
  if (!variant.value || variant.value === 'default') return {};
  
  // Generate shorter delays for more visible sparkle animation
  const delay1 = Math.random() * 2 + 0.5; // 0.5-2.5 seconds
  const delay2 = Math.random() * 3 + 1; // 1-4 seconds
  
  // Generate random offsets for gradient patterns to make each card unique
  const gradientOffset1 = Math.random() * 40 - 20; // -20px to +20px
  const gradientOffset2 = Math.random() * 60 - 30; // -30px to +30px
  const scaleVariation = 0.8 + Math.random() * 0.4; // 0.8 to 1.2 scale
  
  return {
    '--sparkle-delay': `${delay1}s`,
    '--sparkle-delay-2': `${delay2}s`,
    '--gradient-offset-1': `${gradientOffset1}px`,
    '--gradient-offset-2': `${gradientOffset2}px`,
    '--gradient-scale': scaleVariation
  };
});
</script>
