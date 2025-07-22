<template>
    <div
        :class="[
            'themed-card themed-shadow-lg flex flex-col gap-6 rounded-xl border bg-card py-6 text-card-foreground',
            className,
        ]"
        :data-theme="variant || 'default'"
    >
          <!-- Star Icon for Special Variants -->
          <div
              v-if="variant && variant !== 'default'"
              class="absolute top-2 right-2 z-10"
          >
              <StarIcon :variant="variant" />
          </div>

          <!-- Sparkle Animation Overlay -->
          <div 
            v-if="variant && variant !== 'default'" 
            class="themed-sparkle" 
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

// Generate random delays for sparkle animation to make it "occasional"
const sparkleStyle = computed(() => {
  if (!variant.value || variant.value === 'default') return {};
  
  // Generate shorter delays for more visible sparkle animation
  const delay1 = Math.random() * 2 + 0.5; // 0.5-2.5 seconds
  const delay2 = Math.random() * 3 + 1; // 1-4 seconds
  
  return {
    '--sparkle-delay': `${delay1}s`,
    '--sparkle-delay-2': `${delay2}s`
  };
});
</script>
