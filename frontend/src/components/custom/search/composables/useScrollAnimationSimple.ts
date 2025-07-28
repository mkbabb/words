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
    
    // State machine for search bar sizing
    // Priority order: focused/hovered/dropdowns > unfocused > scroll-based
    
    // State 1: Interactive states - always full size
    if (isFocused.value || isHovered.value || hasDropdowns.value) {
      return {
        maxWidth: responsiveMaxWidth,
        transform: 'scale(1)',
        opacity: '1',
        transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      }
    }
    
    // State 2: Unfocused - apply baseline shrink regardless of scroll position
    // This ensures the search bar is never fully expanded when not in use
    const baselineShrink = 0.35 // Apply 35% shrink when unfocused for more noticeable effect
    
    // State 3: Combine baseline shrink with scroll-based shrink
    // The final progress is the maximum of baseline shrink and scroll progress
    const effectiveProgress = Math.max(baselineShrink, Math.min(progress, 1))
    
    // Continuous scale transition - more aggressive for unfocused state
    const scale = 1 - effectiveProgress * 0.15 // Increased from 0.12 to 0.15
    
    // Enhanced opacity transition for unfocused state
    // Immediate opacity reduction when unfocused
    const baseOpacity = 0.85 // Lower base opacity when unfocused
    const opacityReduction = effectiveProgress * 0.2 // More aggressive opacity reduction
    const opacity = Math.max(0.65, baseOpacity - opacityReduction) // Don't go below 0.65
    
    // Continuous width interpolation
    const maxWidthStart = 32 // 32rem
    const maxWidthEnd = 24 // 24rem
    const interpolatedWidth =
      maxWidthStart - effectiveProgress * (maxWidthStart - maxWidthEnd)
    const currentMaxWidth = `min(${interpolatedWidth}rem, calc(100vw - ${2 + effectiveProgress * 2}rem))`
    
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