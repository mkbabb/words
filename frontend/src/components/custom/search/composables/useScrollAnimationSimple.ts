import { computed, type Ref } from 'vue'

/**
 * Simple scroll animation composable that matches the SearchBar's usage
 */
export function useScrollAnimationSimple(
  scrollProgress: Ref<number>,
  isHovered: Ref<boolean>,
  isFocused: Ref<boolean>,
  hasDropdowns: Ref<boolean>
) {
  // Container style with smooth transitions
  const containerStyle = computed(() => {
    // Use the scroll progress directly as it's already normalized (0-1)
    const progress = scrollProgress.value
    
    // Use smaller responsive widths for better desktop experience
    const responsiveMaxWidth = 'min(32rem, calc(100vw - 2rem))'
    
    // Focused/hovered states or dropdowns shown: full size but responsive
    if (isFocused.value || isHovered.value || hasDropdowns.value) {
      return {
        maxWidth: responsiveMaxWidth,
        transform: 'scale(1)',
        opacity: '1',
        transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      }
    }
    
    // Smooth continuous shrinking based on scroll progress
    const clampedProgress = Math.max(0, Math.min(progress, 1))
    
    // Continuous scale transition from 1.0 to 0.88
    const scale = 1 - clampedProgress * 0.12
    
    // Continuous opacity transition from 1.0 to 0.92
    const opacity = 1 - clampedProgress * 0.08
    
    // Continuous width interpolation
    const maxWidthStart = 32 // 32rem
    const maxWidthEnd = 24 // 24rem
    const interpolatedWidth =
      maxWidthStart - clampedProgress * (maxWidthStart - maxWidthEnd)
    const currentMaxWidth = `min(${interpolatedWidth}rem, calc(100vw - ${2 + clampedProgress * 2}rem))`
    
    return {
      maxWidth: currentMaxWidth,
      transform: `scale(${scale})`,
      opacity: opacity.toString(),
      transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
    }
  })
  
  // Simple update method that does nothing (for compatibility)
  const updateScrollState = () => {
    // No-op for compatibility
  }
  
  return {
    containerStyle,
    updateScrollState
  }
}