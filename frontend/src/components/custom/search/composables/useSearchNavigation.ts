import { ref, nextTick, Ref } from 'vue';
import { useAppStore } from '@/stores';

interface UseSearchNavigationOptions {
  searchResultsComponent: Ref<any>;
}

/**
 * Handles search result navigation with scroll-to-view functionality
 * Manages arrow key navigation and visual feedback
 */
export function useSearchNavigation(options: UseSearchNavigationOptions) {
  const store = useAppStore();
  const { searchResultsComponent } = options;
  
  const selectedIndex = ref(0);

  /**
   * Navigate through search results with proper scroll-to-view
   */
  const navigateResults = (direction: number) => {
    if (store.searchResults.length === 0) return;

    selectedIndex.value = Math.max(
      0,
      Math.min(
        store.searchResults.length - 1,
        selectedIndex.value + direction
      )
    );

    store.searchSelectedIndex = selectedIndex.value;
    
    // Scroll the selected item into view with improved logic
    nextTick(() => {
      const container = searchResultsComponent.value?.container;
      const selectedElement = searchResultsComponent.value?.resultRefs?.[selectedIndex.value];
      
      if (!container || !selectedElement) return;
      
      const containerRect = container.getBoundingClientRect();
      const elementRect = selectedElement.getBoundingClientRect();
      
      // Calculate if element is outside visible area
      const isAbove = elementRect.top < containerRect.top;
      const isBelow = elementRect.bottom > containerRect.bottom;
      
      if (isAbove || isBelow) {
        // Scroll within the container only, not the entire page
        const scrollTop = container.scrollTop;
        const containerHeight = container.offsetHeight;
        const elementTop = selectedElement.offsetTop;
        const elementHeight = selectedElement.offsetHeight;
        
        if (isAbove) {
          // Scroll up to show the element at the top with smooth behavior
          container.scrollTo({
            top: elementTop,
            behavior: 'smooth'
          });
        } else if (isBelow) {
          // Scroll down to show the element at the bottom with smooth behavior
          container.scrollTo({
            top: elementTop + elementHeight - containerHeight,
            behavior: 'smooth'
          });
        }
      }
    });
  };

  /**
   * Reset selected index when results change
   */
  const resetSelection = () => {
    selectedIndex.value = 0;
    store.searchSelectedIndex = 0;
  };

  /**
   * Sync selected index with store
   */
  const syncSelectedIndex = () => {
    selectedIndex.value = store.searchSelectedIndex;
  };

  return {
    // State
    selectedIndex,
    
    // Methods
    navigateResults,
    resetSelection,
    syncSelectedIndex,
  };
}