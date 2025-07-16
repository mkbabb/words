<template>
  <div
    :class="[
      'text-card-foreground relative overflow-hidden rounded-2xl transition-all duration-300',
      'card-shadow',
      variant !== 'default'
        ? `card-${variant}`
        : 'bg-card hover:card-shadow-hover',
      className,
    ]"
    :data-variant="variant"
  >
    <!-- Star Icon for Special Variants -->
    <div
      v-if="variant && variant !== 'default'"
      class="absolute top-4 right-4 z-10"
    >
      <StarIcon :variant="variant" />
    </div>

    <!-- Sparkle Animation Overlay -->
    <div
      v-if="variant && variant !== 'default'"
      :class="`pointer-events-none absolute inset-0 sparkle-${variant}`"
    />

    <!-- Content -->
    <slot />
  </div>
</template>

<script setup lang="ts">
import { toRefs } from 'vue';
import StarIcon from './StarIcon.vue';

type CardVariant = 'default' | 'gold' | 'silver' | 'bronze';

interface ThemedCardProps {
  variant?: CardVariant;
  className?: string;
}

const props = defineProps<ThemedCardProps>();

// Clean prop handling
const { variant, className } = toRefs(props);
</script>
