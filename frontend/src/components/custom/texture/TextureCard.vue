<template>
  <div
    :class="[
      'themed-card themed-shadow-lg flex flex-col gap-6 rounded-xl border bg-card py-6 text-card-foreground relative',
      textureClasses,
      className,
    ]"
    :data-theme="variant || 'default'"
    :data-texture-type="textureType"
    :style="combinedStyles"
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

    <!-- Custom Texture Overlay (when texture override is enabled) -->
    <div
      v-if="textureOverride && textureEnabled"
      class="absolute inset-0 pointer-events-none z-10"
      :style="textureOverlayStyles"
    />

    <!-- Content -->
    <slot />
  </div>
</template>

<script setup lang="ts">
import { toRefs, computed } from 'vue'
import { StarIcon } from '@/components/custom/icons'
import { useTextureSystem } from '@/composables/useTextureSystem'
import type { CardVariant, TextureType, TextureIntensity } from '@/types'

interface Props {
  /** Card theme variant */
  variant?: CardVariant
  /** Additional CSS classes */
  className?: string
  /** Override texture type for this card */
  textureType?: TextureType
  /** Override texture intensity */
  intensity?: TextureIntensity
  /** Override texture blend mode */
  blendMode?: 'multiply' | 'overlay' | 'soft-light' | 'normal'
  /** Override texture opacity */
  opacity?: number
  /** Enable custom texture overlay (independent of themed system) */
  textureOverride?: boolean
  /** Enable/disable all texture effects */
  textureEnabled?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default',
  className: '',
  textureType: 'clean',
  intensity: 'subtle',
  blendMode: 'multiply',
  opacity: 0.03,
  textureOverride: false,
  textureEnabled: true,
})

const { variant, className, textureType, intensity, blendMode, opacity, textureOverride, textureEnabled } = toRefs(props)

// Use texture system for texture classes and styles
const { textureStyles, textureClasses } = useTextureSystem({
  enabled: textureEnabled.value && textureOverride.value,
  options: {
    type: textureType.value,
    intensity: intensity.value,
    blendMode: blendMode.value,
    opacity: opacity.value,
  },
})

// Generate random variations for sparkle animation and gradient patterns (from original ThemedCard)
const sparkleStyle = computed(() => {
  if (!variant.value || variant.value === 'default') return {}
  
  const delay1 = Math.random() * 2 + 0.5
  const delay2 = Math.random() * 3 + 1
  const gradientOffset1 = Math.random() * 40 - 20
  const gradientOffset2 = Math.random() * 60 - 30
  const scaleVariation = 0.8 + Math.random() * 0.4
  
  return {
    '--sparkle-delay': `${delay1}s`,
    '--sparkle-delay-2': `${delay2}s`,
    '--gradient-offset-1': `${gradientOffset1}px`,
    '--gradient-offset-2': `${gradientOffset2}px`,
    '--gradient-scale': scaleVariation
  }
})

// Texture overlay styles for custom texture override
const textureOverlayStyles = computed(() => {
  if (!textureOverride.value || !textureEnabled.value) return {}
  
  return {
    ...textureStyles.value,
    borderRadius: 'inherit',
  }
})

// Combined styles for the card
const combinedStyles = computed(() => {
  const styles: Record<string, string | number> = {}
  
  // Add sparkle styles (ensuring proper typing)
  const sparkleValues = sparkleStyle.value
  Object.entries(sparkleValues).forEach(([key, value]) => {
    if (value !== undefined) {
      styles[key] = value
    }
  })
  
  // Add texture variables for CSS integration
  if (textureEnabled.value) {
    styles['--card-texture-type'] = textureType.value
    styles['--card-texture-intensity'] = intensity.value
    styles['--card-texture-opacity'] = opacity.value
  }
  
  return styles
})
</script>

<style scoped>
/* Enhanced texture integration with existing themed-card system */
.themed-card[data-texture-type] {
  /* The texture is already applied via the themed-cards.css system */
  /* This just ensures proper z-indexing for custom overlays */
}

.themed-card[data-texture-type] > :deep(*:not(.absolute)) {
  position: relative;
  z-index: 2;
}
</style>