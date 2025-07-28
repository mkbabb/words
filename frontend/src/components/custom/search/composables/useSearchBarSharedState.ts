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
    selectedSources: ['wiktionary'],
    selectedLanguages: ['en'],
    noAI: true,
    
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
        state.forceRefreshMode = store.forceRefreshMode;
        state.selectedSources = store.selectedSources || ['wiktionary'];
        state.selectedLanguages = store.selectedLanguages || ['en'];
        state.noAI = store.noAI !== undefined ? store.noAI : true;
        
        // Restore persisted search state
        if (store.searchQuery) {
            state.query = store.searchQuery;
        }
        if (store.sessionState?.isAIQuery) {
            state.isAIQuery = true;
            state.showSparkle = true;
            // Use aiQueryText if available, otherwise use searchQuery
            if (store.sessionState.aiQueryText) {
                state.query = store.sessionState.aiQueryText;
            }
        }
        
        // Validate persisted mode - ensure it's valid for current state
        if (state.mode === 'suggestions' && (!store.wordSuggestions || !store.wordSuggestions.suggestions?.length)) {
            // Can't be in suggestions mode without suggestions, fall back to dictionary
            state.mode = 'dictionary';
            store.mode = 'dictionary';
        } else if ((state.mode === 'dictionary' || state.mode === 'thesaurus') && !store.currentEntry) {
            // Can't be in dictionary/thesaurus mode without a current entry
            if (store.wordSuggestions && store.wordSuggestions.suggestions?.length > 0) {
                state.mode = 'suggestions';
                store.mode = 'suggestions';
            }
        }
        
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
    
    // Watch for changes in local forceRefreshMode and sync to store
    watch(() => state.forceRefreshMode, (newMode) => {
        if (store.forceRefreshMode !== newMode) {
            store.forceRefreshMode = newMode;
        }
    });
    
    // Watch for changes in store forceRefreshMode and sync to local state
    watch(() => store.forceRefreshMode, (newMode) => {
        if (state.forceRefreshMode !== newMode) {
            state.forceRefreshMode = newMode;
        }
    });
    
    // Watch for changes in local selectedSources and sync to store
    watch(() => state.selectedSources, (newSources) => {
        store.selectedSources = newSources;
    }, { deep: true });
    
    // Watch for changes in store selectedSources and sync to local state
    watch(() => store.selectedSources, (newSources) => {
        if (JSON.stringify(state.selectedSources) !== JSON.stringify(newSources)) {
            state.selectedSources = newSources;
        }
    }, { deep: true });
    
    // Watch for changes in local selectedLanguages and sync to store
    watch(() => state.selectedLanguages, (newLanguages) => {
        store.selectedLanguages = newLanguages;
    }, { deep: true });
    
    // Watch for changes in store selectedLanguages and sync to local state
    watch(() => store.selectedLanguages, (newLanguages) => {
        if (JSON.stringify(state.selectedLanguages) !== JSON.stringify(newLanguages)) {
            state.selectedLanguages = newLanguages;
        }
    }, { deep: true });
    
    // Watch for changes in local noAI and sync to store
    watch(() => state.noAI, (newNoAI) => {
        if (store.noAI !== newNoAI) {
            store.noAI = newNoAI;
        }
    });
    
    // Watch for changes in store noAI and sync to local state
    watch(() => store.noAI, (newNoAI) => {
        if (state.noAI !== newNoAI) {
            state.noAI = newNoAI;
        }
    });
    
    return {
        state,
        iconOpacity,
        canToggleMode
    };
}