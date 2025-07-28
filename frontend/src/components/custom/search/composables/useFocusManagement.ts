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

    // Restore search results if available
    if (
      store.sessionState?.searchResults?.length > 0 &&
      store.searchQuery.length >= 2
    ) {
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
      if (isInteractingWithSearchArea.value) return;

      store.isSearchBarFocused = false;
      emit('blur');

      // Hide results on blur
      store.showSearchResults = false;
      store.searchResults = [];
      store.isSearching = false;
    }, 150);
  };

  /**
   * Track interaction with search area to prevent blur
   */
  const handleSearchAreaInteraction = () => {
    isInteractingWithSearchArea.value = true;
    setTimeout(() => {
      isInteractingWithSearchArea.value = false;
    }, 100);
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