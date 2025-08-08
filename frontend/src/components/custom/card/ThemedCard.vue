<template>
  <Card
    :class="[
      'themed-card themed-shadow-lg',
      className,
    ]"
    :data-theme="variant || 'default'"
    :texture-enabled="textureEnabled"
    :texture-type="textureType"
    :texture-intensity="textureIntensity"
    :custom-styles="sparkleStyle"
  >
    <!-- Star Icon - smaller size -->
    <StarIcon 
      v-if="variant && variant !== 'default' && !hideStar"
      :variant="variant" 
      class="absolute top-1.5 right-1.5 z-30 h-6 w-6"
    />

    <!-- Border Shimmer (optional) -->
    <BorderShimmer
      v-if="borderShimmer && variant && variant !== 'default'"
      class="pointer-events-none"
      :active="true"
      :color="borderColor"
      :thickness="3"
      :border-width="2"
      :duration="2800"
    />

    <!-- Sparkle Animation Overlay -->
    <div 
      v-if="variant && variant !== 'default'" 
      class="themed-sparkle absolute inset-0 pointer-events-none w-full h-full" 
      :style="sparkleStyle"
    />

    <!-- Content -->
    <slot />
  </Card>
</template>

<script setup lang="ts">
import { toRefs, computed } from 'vue'
import { StarIcon } from '@/components/custom/icons'
import { BorderShimmer } from '@/components/custom/animation'
import Card from './Card.vue'
import type { CardVariant, TextureType, TextureIntensity } from '@/types'

interface Props {
  variant?: CardVariant
  className?: string
  textureEnabled?: boolean
  textureType?: TextureType
  textureIntensity?: TextureIntensity
  hideStar?: boolean
  borderShimmer?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  className: '',
  textureEnabled: true,
  textureType: 'clean',
  textureIntensity: 'subtle',
  hideStar: false,
  borderShimmer: true,
})

// Clean prop handling
const { variant, className, textureEnabled, textureType, textureIntensity, hideStar, borderShimmer } = toRefs(props)

// Generate random variations for sparkle animation and gradient patterns
const sparkleStyle = computed((): Record<string, string | number> => {
  if (!variant.value || variant.value === 'default') return {}
  
  // Generate shorter delays for more visible sparkle animation
  const delay1 = Math.random() * 4 + 2 // 2-6 seconds
  const delay2 = Math.random() * 6 + 3 // 3-9 seconds
  
  // Generate random offsets for gradient patterns to make each card unique
  const gradientOffset1 = Math.random() * 40 - 20 // -20px to +20px
  const gradientOffset2 = Math.random() * 60 - 30 // -30px to +30px
  const scaleVariation = 0.8 + Math.random() * 0.4 // 0.8 to 1.2 scale
  const shimmerDuration = Math.floor(14000 + Math.random() * 10000) // 14-24s
  const sparkleOpacity = (0.14 + Math.random() * 0.08).toFixed(2) // 0.14-0.22
  
  return {
    '--sparkle-delay': `${delay1}s`,
    '--sparkle-delay-2': `${delay2}s`,
    '--gradient-offset-1': `${gradientOffset1}px`,
    '--gradient-offset-2': `${gradientOffset2}px`,
    '--gradient-scale': scaleVariation.toString(),
    '--shimmer-duration': `${shimmerDuration}ms`,
    '--sparkle-opacity': sparkleOpacity,
  }
})

// Choose border shimmer color based on variant
const borderColor = computed(() => {
  switch (variant.value) {
    case 'gold':
      return 'rgb(251 191 36)'
    case 'silver':
      return 'rgb(203 213 225)'
    case 'bronze':
      return 'rgb(251 146 60)'
    default:
      return 'rgb(99 102 241)'
  }
})
</script>
