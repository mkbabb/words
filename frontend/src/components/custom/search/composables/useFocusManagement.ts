import { ref, nextTick, Ref } from 'vue';
import { useAppStore } from '@/stores';

interface UseFocusManagementOptions {
  searchInputComponent: Ref<any>;
  emit: (event: string, ...args: any[]) => void;
}

/**
 * Manages focus state and textarea resizing for the search input
 * Handles session restoration and interaction tracking
 */
export function useFocusManagement(options: UseFocusManagementOptions) {
  const store = useAppStore();
  const { searchInputComponent, emit } = options;

  const isInteractingWithSearchArea = ref(false);
  const blurTimer = ref<ReturnType<typeof setTimeout> | undefined>();

  /**
   * Handle focus event with textarea resizing and session restoration
   */
  const handleFocus = () => {
    store.isSearchBarFocused = true;
    emit('focus');

    // Force textarea resize on focus
    nextTick(() => {
      if (searchInputComponent.value?.element?.value) {
        const textarea = searchInputComponent.value.element.value;
        if (textarea && textarea.style) {
          textarea.style.height = 'auto';
          const scrollHeight = textarea.scrollHeight;
          textarea.style.height = `${scrollHeight}px`;
        }
      }
    });

    // Only restore search results if we're in lookup mode and there's an active query
    // Don't auto-show results when just switching modes or focusing
    console.log('🔍 FOCUS MANAGEMENT - handleFocus called', {
      searchMode: store.searchMode,
      sessionResults: store.sessionState?.searchResults?.length || 0,
      searchQuery: store.searchQuery,
      queryLength: store.searchQuery.length,
      isDirectLookup: store.isDirectLookup,
      isSwitchingModes: store.isSwitchingModes
    });
    
    if (
      store.searchMode === 'lookup' &&
      store.sessionState?.searchResults?.length > 0 &&
      store.searchQuery.length >= 2 &&
      !store.isDirectLookup // Don't show if we're doing a direct lookup
    ) {
      console.log('🔍 FOCUS MANAGEMENT - RESTORING SEARCH RESULTS AND SHOWING DROPDOWN');
      store.searchResults = store.sessionState.searchResults.slice(0, 8);
      store.showSearchResults = true;
    }
  };

  /**
   * Handle blur event with delayed hiding
   */
  const handleBlur = () => {
    if (blurTimer.value) {
      clearTimeout(blurTimer.value);
    }

    blurTimer.value = setTimeout(() => {
      // If user is still interacting with search area, don't blur
      if (isInteractingWithSearchArea.value) return;

      store.isSearchBarFocused = false;
      emit('blur');

      // Hide results on blur only if we're not interacting with search area
      store.showSearchResults = false;
      store.searchResults = [];
      store.isSearching = false;
    }, 200); // Increased delay to 200ms for better UX
  };

  /**
   * Track interaction with search area to prevent blur
   */
  const handleSearchAreaInteraction = () => {
    isInteractingWithSearchArea.value = true;
    // Clear any existing timer
    if (blurTimer.value) {
      clearTimeout(blurTimer.value);
    }
    // Reset interaction flag after a longer delay to ensure clicks are processed
    setTimeout(() => {
      isInteractingWithSearchArea.value = false;
    }, 300);
  };

  /**
   * Focus the search input programmatically
   */
  const focusInput = () => {
    searchInputComponent.value?.focus();
  };

  /**
   * Cleanup timers
   */
  const cleanup = () => {
    if (blurTimer.value) {
      clearTimeout(blurTimer.value);
    }
  };

  return {
    // State
    isInteractingWithSearchArea,
    
    // Methods
    handleFocus,
    handleBlur,
    handleSearchAreaInteraction,
    focusInput,
    cleanup,
  };
}