import { ref, computed, watch, type Ref } from 'vue'
import { useScroll } from '@vueuse/core'

interface UseScrollAnimationOptions {
  scrollInflectionPoint?: number
  currentState: Ref<'normal' | 'hovering' | 'focused'>
  isContainerHovered: Ref<boolean>
  isFocused: Ref<boolean>
  showControls: Ref<boolean>
  showResults: Ref<boolean>
  transitionToState: (state: 'normal' | 'hovering' | 'focused') => void
}

/**
 * Composable for managing scroll-based animations
 * Handles scroll tracking, opacity transitions, and container scaling
 */
export function useScrollAnimation({
  scrollInflectionPoint = 0.25,
  currentState,
  isContainerHovered,
  isFocused,
  showControls,
  showResults,
  transitionToState,
}: UseScrollAnimationOptions) {
  // Scroll state
  const scrollProgress = ref(0)
  const documentHeight = ref(0)
  let scrollAnimationFrame: number | undefined
  
  // Scroll tracking
  const { y: scrollY } = useScroll(window)
  
  // Initialize document height
  const initializeDocumentHeight = () => {
    documentHeight.value = Math.max(
      document.body.scrollHeight,
      document.body.offsetHeight,
      document.documentElement.clientHeight,
      document.documentElement.scrollHeight,
      document.documentElement.offsetHeight
    )
  }
  
  // Update scroll state
  const updateScrollState = () => {
    if (scrollAnimationFrame) return
    
    scrollAnimationFrame = requestAnimationFrame(() => {
      const maxScroll = Math.max(
        documentHeight.value - window.innerHeight,
        1
      )
      
      // Don't engage scrolling behavior if there's nothing to scroll
      if (maxScroll <= 10) {
        scrollProgress.value = 0
        scrollAnimationFrame = undefined
        return
      }
      
      // Simple continuous progress calculation
      scrollProgress.value = Math.min(scrollY.value / maxScroll, 1)
      
      // Update state for icon opacity and container styling
      if (isFocused.value && currentState.value !== 'focused') {
        transitionToState('focused')
      } else if (
        isContainerHovered.value &&
        currentState.value !== 'hovering' &&
        !isFocused.value
      ) {
        transitionToState('hovering')
      } else if (
        !isFocused.value &&
        !isContainerHovered.value &&
        (currentState.value === 'focused' || currentState.value === 'hovering')
      ) {
        transitionToState('normal')
      }
      
      scrollAnimationFrame = undefined
    })
  }
  
  // Computed opacity for smooth icon fade-out
  const iconOpacity = computed(() => {
    // Always full opacity when focused or hovered
    if (isFocused.value || isContainerHovered.value) {
      return 1
    }
    
    // Don't fade when either dropdown is showing
    if (showControls.value || showResults.value) {
      return 1
    }
    
    // Continuous fade based on scroll progress relative to inflection point
    const progress = Math.min(
      scrollProgress.value / scrollInflectionPoint,
      1
    )
    
    // Start fading at 40% of the way to inflection point, fully hidden at 85%
    const fadeStart = 0.4
    const fadeEnd = 0.85
    
    if (progress <= fadeStart) {
      return 1 // Full opacity
    } else if (progress >= fadeEnd) {
      return 0.1 // Nearly hidden but still interactive
    } else {
      // Smooth cubic easing for natural fade
      const fadeProgress = (progress - fadeStart) / (fadeEnd - fadeStart)
      const easedProgress = 1 - Math.pow(1 - fadeProgress, 3) // Cubic ease-out
      return 1 - easedProgress * 0.9 // Fade from 1 to 0.1
    }
  })
  
  // Container style with smooth transitions
  const containerStyle = computed(() => {
    const progress = Math.min(
      scrollProgress.value / scrollInflectionPoint,
      1
    )
    
    // Use smaller responsive widths for better desktop experience
    const responsiveMaxWidth = 'min(32rem, calc(100vw - 2rem))'
    
    // Focused/hovered states or dropdowns shown: full size but responsive
    if (
      isFocused.value ||
      isContainerHovered.value ||
      showControls.value ||
      showResults.value
    ) {
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
  
  // Results container style
  const resultsContainerStyle = computed(() => {
    return {
      paddingTop: '0px',
      transition: 'all 300ms cubic-bezier(0.25, 0.1, 0.25, 1)',
    }
  })
  
  // Setup and cleanup
  const setup = () => {
    initializeDocumentHeight()
    window.addEventListener('resize', initializeDocumentHeight)
    
    // Watch scroll changes
    const unwatch = watch(scrollY, () => {
      updateScrollState()
    })
    
    return () => {
      unwatch()
      window.removeEventListener('resize', initializeDocumentHeight)
      if (scrollAnimationFrame) {
        cancelAnimationFrame(scrollAnimationFrame)
      }
    }
  }
  
  return {
    // State
    scrollProgress,
    documentHeight,
    
    // Computed
    iconOpacity,
    containerStyle,
    resultsContainerStyle,
    
    // Methods
    initializeDocumentHeight,
    updateScrollState,
    setup,
  }
}