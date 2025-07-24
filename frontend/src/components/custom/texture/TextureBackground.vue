<template>
  <div
    :class="[
      'texture-background',
      ...textureClasses,
      className
    ]"
    :style="combinedStyles"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
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
  customStyles: () => ({}),
})

// Use texture system with local props
const { textureStyles, textureClasses } = useTextureSystem({
  enabled: props.enabled,
  options: {
    type: props.textureType,
    intensity: props.intensity,
    blendMode: props.blendMode,
    opacity: props.opacity,
  },
})

// Combine texture styles with custom styles
const combinedStyles = computed(() => ({
  ...textureStyles.value,
  ...props.customStyles,
}))
</script>

<style scoped>
.texture-background {
  position: relative;
  width: 100%;
  height: 100%;
}

/* Ensure child content appears above texture */
.texture-background > :deep(*) {
  position: relative;
  z-index: 1;
}
</style>