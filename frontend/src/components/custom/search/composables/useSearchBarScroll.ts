import { computed, watch } from 'vue';
import { useSearchBarUI } from './useSearchBarUI';
import { useScrollAnimationSimple } from './useScrollAnimationSimple';
import { useStores } from '@/stores';

interface UseSearchBarScrollOptions {
  shrinkPercentage: () => number;
}

/**
 * Focused composable for SearchBar scroll animations and effects
 * Handles scroll progress, container styling, and scroll-based UI updates
 */
export function useSearchBarScroll(options: UseSearchBarScrollOptions) {
  const { searchBar } = useStores();
  const { uiState } = useSearchBarUI();
  const { shrinkPercentage } = options;

  // Scroll animation setup
  const { containerStyle, updateScrollState } = useScrollAnimationSimple(
    computed(() => uiState.scrollProgress),
    computed(() => uiState.isContainerHovered),
    computed(() => searchBar.isSearchBarFocused),
    computed(() => searchBar.showSearchControls || searchBar.showSearchResults)
  );

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

  // Update scroll state when relevant properties change
  const updateScrollAnimations = () => {
    updateScrollState();
  };

  return {
    // Computed
    containerStyle,
    
    // Methods
    updateScrollAnimations,
  };
}