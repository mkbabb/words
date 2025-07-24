<template>
  <div
    v-if="enabled"
    :class="[
      'texture-overlay',
      ...textureClasses,
      className
    ]"
    :style="overlayStyles"
  />
</template>

<script setup lang="ts">
import { computed, toRefs } from 'vue'
import { useTextureSystem } from '@/composables/useTextureSystem'
import type { TextureType, TextureIntensity } from '@/types'

interface Props {
  /** Texture type to apply */
  textureType?: TextureType
  /** Texture intensity */
  intensity?: TextureIntensity
  /** Blend mode for texture */
  blendMode?: 'multiply' | 'overlay' | 'soft-light' | 'normal'
  /** Custom opacity override */
  opacity?: number
  /** Enable/disable texture */
  enabled?: boolean
  /** Additional CSS classes */
  className?: string
  /** Position mode - absolute overlay or relative element */
  position?: 'absolute' | 'relative' | 'fixed'
  /** Z-index for overlay positioning */
  zIndex?: number
  /** Inset values for absolute positioning */
  inset?: string | number
  /** Custom styles to merge */
  customStyles?: Record<string, string | number>
}

const props = withDefaults(defineProps<Props>(), {
  textureType: 'clean',
  intensity: 'subtle',
  blendMode: 'multiply',
  opacity: 0.03,
  enabled: true,
  className: '',
  position: 'absolute',
  zIndex: 0,
  inset: 0,
  customStyles: () => ({}),
})

const { enabled, position, zIndex, inset, customStyles } = toRefs(props)

// Use texture system with local props
const { textureStyles, textureClasses } = useTextureSystem({
  enabled: enabled.value,
  options: {
    type: props.textureType,
    intensity: props.intensity,
    blendMode: props.blendMode,
    opacity: props.opacity,
  },
})

// Compute overlay positioning styles
const positionStyles = computed(() => {
  const baseStyles: Record<string, string | number> = {
    position: position.value,
    zIndex: zIndex.value,
    pointerEvents: 'none',
  }

  // Add inset values for absolute/fixed positioning
  if (position.value === 'absolute' || position.value === 'fixed') {
    if (typeof inset.value === 'number') {
      baseStyles.top = `${inset.value}px`
      baseStyles.right = `${inset.value}px`
      baseStyles.bottom = `${inset.value}px`
      baseStyles.left = `${inset.value}px`
    } else {
      baseStyles.inset = inset.value
    }
  }

  return baseStyles
})

// Combine all styles
const overlayStyles = computed(() => ({
  ...positionStyles.value,
  ...textureStyles.value,
  ...customStyles.value,
}))
</script>

<style scoped>
.texture-overlay {
  /* Ensure texture overlays don't interfere with content */
  pointer-events: none;
  user-select: none;
}

/* Position variants */
.texture-overlay[style*="position: absolute"] {
  border-radius: inherit;
}

.texture-overlay[style*="position: fixed"] {
  border-radius: 0;
}

.texture-overlay[style*="position: relative"] {
  width: 100%;
  height: 100%;
}
</style>