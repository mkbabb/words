import { computed, watch, ref, onMounted, onUnmounted } from 'vue';
import { useSearchBarUI } from './useSearchBarUI';
import { useStores } from '@/stores';

interface UseSearchBarScrollOptions {
  shrinkPercentage: () => number;
}

/**
 * Unified composable for SearchBar scroll animations and effects
 * Handles scroll progress, container styling, and responsive behavior
 */
export function useSearchBarScroll(options: UseSearchBarScrollOptions) {
  const { searchBar } = useStores();
  const { uiState } = useSearchBarUI();
  const { shrinkPercentage } = options;

  // Track viewport width for responsive behavior
  const viewportWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024);
  
  const updateViewportWidth = () => {
    viewportWidth.value = window.innerWidth;
  };
  
  onMounted(() => {
    window.addEventListener('resize', updateViewportWidth);
    updateViewportWidth();
  });
  
  onUnmounted(() => {
    window.removeEventListener('resize', updateViewportWidth);
  });

  // Container style with smooth transitions
  const containerStyle = computed(() => {
    // Use the scroll progress directly as it's already normalized (0-1)
    const progress = uiState.scrollProgress;
    
    // Use different widths for mobile vs desktop
    const isMobile = viewportWidth.value < 640;
    const mobileMaxWidth = 'calc(100vw - 0.5rem)'; // Nearly full width with minimal padding
    const desktopMaxWidth = 'min(32rem, calc(100vw - 2rem))';
    
    // Select appropriate max width based on viewport
    const responsiveMaxWidth = isMobile ? mobileMaxWidth : desktopMaxWidth;
    
    // State machine for search bar sizing
    // Priority order: focused/hovered/dropdowns > unfocused > scroll-based
    
    // State 1: Interactive states - always full size
    if (searchBar.isFocused || uiState.isContainerHovered || 
        searchBar.showSearchControls || searchBar.showDropdown) {
      return {
        maxWidth: responsiveMaxWidth,
        transform: 'scale(1)',
        opacity: '1',
        transition: 'all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      };
    }
    
    // State 2: Unfocused - apply baseline shrink regardless of scroll position
    const baselineShrink = 0.35; // Apply 35% shrink when unfocused
    
    // State 3: Combine baseline shrink with scroll-based shrink
    const effectiveProgress = Math.max(baselineShrink, Math.min(progress, 1));
    
    // Continuous scale transition
    const scale = 1 - effectiveProgress * 0.15;
    
    // Enhanced opacity transition
    const baseOpacity = 0.85;
    const opacityReduction = effectiveProgress * 0.2;
    const opacity = Math.max(0.65, baseOpacity - opacityReduction);
    
    // Mobile vs desktop behavior
    if (isMobile) {
      // On mobile, maintain consistent full width without scaling
      return {
        maxWidth: 'calc(100vw - 0.5rem)',
        transform: 'scale(1)', // No scaling on mobile
        opacity: opacity.toString(),
        transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      };
    } else {
      // Desktop behavior: interpolate width
      const maxWidthStart = 32; // 32rem
      const maxWidthEnd = 24; // 24rem
      const interpolatedWidth = maxWidthStart - effectiveProgress * (maxWidthStart - maxWidthEnd);
      const currentMaxWidth = `min(${interpolatedWidth}rem, calc(100vw - ${2 + effectiveProgress * 2}rem))`;
      
      return {
        maxWidth: currentMaxWidth,
        transform: `scale(${scale})`,
        opacity: opacity.toString(),
        transition: 'all 0.2s cubic-bezier(0.25, 0.46, 0.45, 0.94)',
      };
    }
  });

  // Update scroll progress from external prop
  watch(shrinkPercentage, (newValue) => {
    uiState.scrollProgress = newValue;
    
    // Debug logging in development
    if (import.meta.env.DEV) {
      console.log('SearchBar scroll update:', {
        shrinkPercentage: newValue,
        scrollProgress: uiState.scrollProgress,
        containerStyle: containerStyle.value,
      });
    }
  }, { immediate: true });

  return {
    // Computed
    containerStyle,
  };
}