import { computed, reactive, shallowRef, watch } from 'vue';
import { useAppStore } from '@/stores';
import type { SearchResult } from '@/types';
import type { SearchBarState, SearchMode } from '../types';

// Modern Vue 3 pattern - shared state composable
// This creates a singleton state that persists across component instances
const state = reactive({
    // Core state
    query: '',
    mode: 'dictionary' as 'dictionary' | 'thesaurus' | 'suggestions', // Default value
    searchMode: 'lookup' as SearchMode, // Default value
    currentState: 'normal' as SearchBarState,
    _initialized: false,
    
    // UI state
    isFocused: false,
    isContainerHovered: false,
    showControls: false,
    showResults: false,
    showExpandModal: false,
    
    // Search state
    isSearching: false,
    searchResults: shallowRef<SearchResult[]>([]),
    selectedIndex: 0,
    
    // AI state
    isAIQuery: false,
    aiSuggestions: [] as string[],
    showSparkle: false,
    showErrorAnimation: false,
    
    // Autocomplete
    autocompleteText: '',
    
    // Scroll state
    scrollProgress: 0,
    documentHeight: 0,
    externalShrinkPercentage: 0,
    
    // Force refresh
    forceRefreshMode: false,
    regenerateRotation: 0,
    
    // Dimensions
    searchBarHeight: 64,
    expandButtonVisible: false,
    
    // Selected options
    selectedSources: ['wiktionary', 'oxford', 'dictionary_com', 'apple_dictionary'],
    selectedLanguages: ['en'],
    
    // Dev mode
    isDevelopment: import.meta.env.DEV
});

// Computed properties
const iconOpacity = computed(() => {
    // Always full opacity when focused or hovered
    if (state.isFocused || state.isContainerHovered) {
        return 1;
    }

    // Don't fade when either dropdown is showing
    if (state.showControls || state.showResults) {
        return 1;
    }

    // Continuous fade based on scroll progress
    // scrollProgress is already normalized (0-1), so use it directly
    const progress = state.scrollProgress;

    // Start fading at 40% of the way to inflection point, fully hidden at 85%
    const fadeStart = 0.4;
    const fadeEnd = 0.85;

    if (progress <= fadeStart) {
        return 1; // Full opacity
    } else if (progress >= fadeEnd) {
        return 0.1; // Nearly hidden but still interactive
    } else {
        // Smooth cubic easing for natural fade
        const fadeProgress = (progress - fadeStart) / (fadeEnd - fadeStart);
        const easedProgress = 1 - Math.pow(1 - fadeProgress, 3); // Cubic ease-out
        return 1 - easedProgress * 0.9; // Fade from 1 to 0.1
    }
});

// Export the shared state and computed properties
export function useSearchBarSharedState() {
    const store = useAppStore();
    
    // Initialize state from store on first use
    if (!state._initialized) {
        state.mode = store.mode as 'dictionary' | 'thesaurus' | 'suggestions';
        state.searchMode = (store.searchMode || 'lookup') as SearchMode;
        state._initialized = true;
    }
    
    const canToggleMode = computed(() => {
        // Check what queries have been made
        const hasWordQuery = !!store.currentEntry;
        const hasSuggestionQuery = !!store.wordSuggestions;
        
        // No queries made - can't toggle
        if (!hasWordQuery && !hasSuggestionQuery) {
            return false;
        }
        
        // Only suggestion query made - must stay in suggestions mode
        if (hasSuggestionQuery && !hasWordQuery) {
            return false;
        }
        
        // Has word query - can toggle between dictionary/thesaurus
        // or to suggestions if suggestion query was also made
        return true;
    });
    
    // Watch for changes in local state mode and sync to store
    watch(() => state.mode, (newMode) => {
        if (store.mode !== newMode) {
            store.mode = newMode;
        }
    });
    
    // Watch for changes in store mode and sync to local state
    watch(() => store.mode, (newMode) => {
        if (state.mode !== newMode) {
            state.mode = newMode;
        }
    });
    
    // Watch for changes in local searchMode and sync to store
    watch(() => state.searchMode, (newMode) => {
        if (store.searchMode !== newMode) {
            store.searchMode = newMode;
        }
    });
    
    // Watch for changes in store searchMode and sync to local state
    watch(() => store.searchMode, (newMode) => {
        if (state.searchMode !== newMode) {
            state.searchMode = newMode;
        }
    });
    
    return {
        state,
        iconOpacity,
        canToggleMode
    };
}