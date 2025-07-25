<template>
  <div
    :class="[
      'card flex flex-col gap-6 rounded-xl border bg-card py-6 text-card-foreground relative',
      textureClasses,
      className,
    ]"
    :style="cardStyles"
  >
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTextureSystem } from '@/composables/useTextureSystem'
import type { TextureType, TextureIntensity } from '@/types'

interface Props {
  /** Additional CSS classes */
  className?: string
  /** Apply texture to card */
  textureEnabled?: boolean
  /** Texture type */
  textureType?: TextureType
  /** Texture intensity */
  textureIntensity?: TextureIntensity
  /** Custom styles */
  customStyles?: Record<string, string | number>
}

const props = withDefaults(defineProps<Props>(), {
  className: '',
  textureEnabled: true,
  textureType: 'clean',
  textureIntensity: 'subtle',
  customStyles: () => ({}),
})

// Texture system integration - using classes only to avoid visibility issues  
const { textureClasses } = useTextureSystem({
  enabled: props.textureEnabled,
  options: {
    type: props.textureType,
    intensity: props.textureIntensity,
    blendMode: 'multiply',
    opacity: 0.03,
  },
})

// Combined styles - only add texture styles, don't override core styles
const cardStyles = computed(() => ({
  ...props.customStyles,
  // Only add background-image, avoid mixBlendMode and opacity on the element itself
  ...(props.textureEnabled ? {
    backgroundImage: `var(--paper-${props.textureType}-texture)`,
    backgroundSize: props.textureIntensity === 'subtle' ? '60px 60px' : 
                   props.textureIntensity === 'medium' ? '80px 80px' : '100px 100px',
    backgroundBlendMode: 'multiply'
  } : {}),
}))
</script>

<style scoped>
.card {
  /* Base card styles */
}

/* Ensure texture is visible with base background */
.card[style*="background"] {
  background-blend-mode: multiply;
}
</style>