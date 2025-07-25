import { ref, computed, watch } from 'vue'
import type { TextureType, TextureIntensity, TextureOptions, TextureConfig } from '@/types'

/**
 * Composable for managing paper texture system
 * Provides reactive texture configuration with CSS custom properties
 */
export function useTextureSystem(initialConfig?: Partial<TextureConfig>) {
  // Reactive state
  const enabled = ref(initialConfig?.enabled ?? true)
  const textureType = ref<TextureType>(initialConfig?.options?.type ?? 'clean')
  const textureIntensity = ref<TextureIntensity>(initialConfig?.options?.intensity ?? 'subtle')
  const blendMode = ref(initialConfig?.options?.blendMode ?? 'multiply')
  const opacity = ref(initialConfig?.options?.opacity ?? 0.03)

  // Computed texture options
  const textureOptions = computed<TextureOptions>(() => ({
    type: textureType.value,
    intensity: textureIntensity.value,
    blendMode: blendMode.value,
    opacity: opacity.value,
  }))

  // Computed texture config
  const textureConfig = computed<TextureConfig>(() => ({
    enabled: enabled.value,
    options: textureOptions.value,
    customCSS: initialConfig?.customCSS,
  }))

  // Get CSS custom property for texture type
  const getTextureVariable = computed(() => {
    const textureMap = {
      clean: '--paper-clean-texture',
      aged: '--paper-aged-texture',
      handmade: '--paper-handmade-texture',
      kraft: '--paper-kraft-texture',
    }
    return textureMap[textureType.value]
  })

  // Get CSS classes for texture intensity
  const getIntensityClass = computed(() => {
    const intensityMap = {
      subtle: 'texture-subtle',
      medium: 'texture-medium',
      strong: 'texture-strong',
    }
    return intensityMap[textureIntensity.value]
  })

  // Generate CSS style object for components - fixed to not break visibility
  const textureStyles = computed(() => {
    if (!enabled.value) return {}

    return {
      '--texture-image': `var(${getTextureVariable.value})`,
      '--texture-opacity': opacity.value.toString(),
      '--texture-blend-mode': blendMode.value,
      backgroundImage: `var(${getTextureVariable.value})`,
      // Don't set mixBlendMode or opacity directly - let CSS classes handle it
      backgroundSize: textureIntensity.value === 'subtle' ? '60px 60px' : 
                     textureIntensity.value === 'medium' ? '80px 80px' : '100px 100px',
    }
  })

  // Generate CSS classes
  const textureClasses = computed(() => {
    if (!enabled.value) return []

    return [
      `texture-paper-${textureType.value}`,
      getIntensityClass.value,
    ]
  })

  // Methods
  const setTextureType = (type: TextureType) => {
    textureType.value = type
  }

  const setTextureIntensity = (intensity: TextureIntensity) => {
    textureIntensity.value = intensity
  }

  const toggleTexture = () => {
    enabled.value = !enabled.value
  }

  const resetToDefaults = () => {
    enabled.value = true
    textureType.value = 'clean'
    textureIntensity.value = 'subtle'
    blendMode.value = 'multiply'
    opacity.value = 0.03
  }

  // Watch for changes and update CSS custom properties on document root
  watch(
    textureConfig,
    (newConfig) => {
      if (typeof document !== 'undefined') {
        const root = document.documentElement
        
        if (newConfig.enabled) {
          root.style.setProperty('--current-texture-type', newConfig.options.type)
          root.style.setProperty('--current-texture-intensity', newConfig.options.intensity)
          root.style.setProperty('--current-texture-opacity', newConfig.options.opacity?.toString() || '0.03')
          root.style.setProperty('--current-texture-blend-mode', newConfig.options.blendMode || 'multiply')
        } else {
          root.style.removeProperty('--current-texture-type')
          root.style.removeProperty('--current-texture-intensity')
          root.style.removeProperty('--current-texture-opacity')
          root.style.removeProperty('--current-texture-blend-mode')
        }
      }
    },
    { deep: true, immediate: true }
  )

  return {
    // State
    enabled,
    textureType,
    textureIntensity,
    blendMode,
    opacity,
    
    // Computed
    textureOptions,
    textureConfig,
    textureStyles,
    textureClasses,
    getTextureVariable,
    getIntensityClass,
    
    // Methods
    setTextureType,
    setTextureIntensity,
    toggleTexture,
    resetToDefaults,
  }
}

/**
 * Global texture system instance for app-wide texture management
 */
let globalTextureSystem: ReturnType<typeof useTextureSystem> | null = null

export function useGlobalTextureSystem() {
  if (!globalTextureSystem) {
    globalTextureSystem = useTextureSystem({
      enabled: true,
      options: {
        type: 'clean',
        intensity: 'subtle',
        blendMode: 'multiply',
        opacity: 0.03,
      },
    })
  }
  return globalTextureSystem
}