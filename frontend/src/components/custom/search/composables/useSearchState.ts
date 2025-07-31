import { reactive, computed } from 'vue';
import { useAppStore } from '@/stores';
import { useSearchBarUI } from './useSearchBarUI';

/**
 * Centralized state management for SearchBar component
 * Provides reactive bindings between component state and store
 */
export function useSearchState() {
  const store = useAppStore();
  const { uiState } = useSearchBarUI();

  // Reactive state with two-way bindings to store
  const state = reactive({
    // Store state (computed getters/setters)
    get query() { 
        return store.searchQuery;
    },
    set query(value) { 
        console.log('🔄 Setting query via useSearchState:', value);
        store.searchQuery = value; 
    },
    get searchResults() { return store.searchResults; },
    set searchResults(value) { store.searchResults = value; },
    get showResults() { return store.showSearchResults; },
    set showResults(value) { store.showSearchResults = value; },
    get isFocused() { return store.isSearchBarFocused; },
    set isFocused(value) { store.isSearchBarFocused = value; },
    get isSearching() { return store.isSearching; },
    set isSearching(_) { /* readonly */ },
    get isAIQuery() { return store.isAIQuery; },
    set isAIQuery(value) { store.isAIQuery = value; },
    get showSparkle() { return store.showSparkle; },
    set showSparkle(value) { store.showSparkle = value; },
    get showErrorAnimation() { return store.showErrorAnimation; },
    set showErrorAnimation(value) { store.showErrorAnimation = value; },
    get selectedIndex() { return store.searchSelectedIndex; },
    set selectedIndex(value) { store.searchSelectedIndex = value; },
    get showControls() { return store.showSearchControls; },
    set showControls(value) { store.showSearchControls = value; },
    get mode() { return store.mode; },
    set mode(value) { store.mode = value; },
    get searchMode() { return store.searchMode; },
    set searchMode(value) { store.searchMode = value; },
    get autocompleteText() { return store.autocompleteText; },
    set autocompleteText(value) { store.autocompleteText = value; },
    get selectedSources() { return store.selectedSources; },
    set selectedSources(value) { store.selectedSources = value; },
    get selectedLanguages() { return store.selectedLanguages; },
    set selectedLanguages(value) { store.selectedLanguages = value; },
    get noAI() { return store.noAI; },
    set noAI(value) { store.noAI = value; },
    get forceRefreshMode() { return store.forceRefreshMode; },
    set forceRefreshMode(value) { store.forceRefreshMode = value; },
    
    // UI state (local)
    get isContainerHovered() { return uiState.isContainerHovered; },
    set isContainerHovered(value) { uiState.isContainerHovered = value; },
    get showExpandModal() { return uiState.showExpandModal; },
    set showExpandModal(value) { uiState.showExpandModal = value; },
    get scrollProgress() { return uiState.scrollProgress; },
    set scrollProgress(value) { uiState.scrollProgress = value; },
    get searchBarHeight() { return uiState.searchBarHeight; },
    set searchBarHeight(value) { uiState.searchBarHeight = value; },
    get expandButtonVisible() { return uiState.expandButtonVisible; },
    set expandButtonVisible(value) { uiState.expandButtonVisible = value; },
    get isDevelopment() { return uiState.isDevelopment; },
    get aiSuggestions() { return store.aiSuggestions; },
    set aiSuggestions(value) { store.aiSuggestions = value; },
    get wordlistFilters() { return store.wordlistFilters; },
    set wordlistFilters(value) { store.wordlistFilters = value; },
    get wordlistChunking() { return store.wordlistChunking; },
    set wordlistChunking(value) { store.wordlistChunking = value; },
    get wordlistSortCriteria() { return store.wordlistSortCriteria; },
    set wordlistSortCriteria(value) { store.wordlistSortCriteria = value; },
  });

  // Computed properties
  const canToggleMode = computed(() => {
    const hasWordQuery = !!store.currentEntry;
    const hasSuggestionQuery = !!store.wordSuggestions;
    
    if (!hasWordQuery && !hasSuggestionQuery) return false;
    if (hasSuggestionQuery && !hasWordQuery) return false;
    return true;
  });

  const placeholder = computed(() => {
    // Hide placeholder when scrolled
    if (state.scrollProgress > 0.3) {
      return '';
    }
    
    // First check searchMode for specific modes
    if (state.searchMode === 'wordlist') {
      return 'words';
    } else if (state.searchMode === 'stage') {
      return 'staging';
    }

    // Default to mode-based placeholders for lookup mode
    return state.mode === 'dictionary'
      ? 'definitions'
      : 'synonyms';
  });

  const resultsContainerStyle = computed(() => ({
    paddingTop: '0px',
    marginTop: state.showControls ? '0.5rem' : '0px',
    transition: 'all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275)',
  }));

  return {
    // State
    state,
    
    // Computed
    canToggleMode,
    placeholder,
    resultsContainerStyle,
  };
}