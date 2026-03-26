import { computed, watch, watchEffect, type Ref } from 'vue';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useContentStore } from '@/stores/content/content';
import { useHistoryStore } from '@/stores/content/history';
import { useLoadingStore } from '@/stores/ui/loading';
import { useAIQueryDetection } from './useAIQueryDetection';
import { useSemanticStatusPoller } from './useSemanticStatusPoller';
import type { useSearchBarUI } from './useSearchBarUI';

interface UseSearchBarBindingsOptions {
    scrollProgress: () => number;
    iconOpacity: Ref<number>;
    uiState: ReturnType<typeof useSearchBarUI>['uiState'];
}

/**
 * Composable that extracts v-model computed bindings, mode-lifecycle watchers,
 * and derived layout computeds from SearchBar.vue.
 */
export function useSearchBarBindings(options: UseSearchBarBindingsOptions) {
    const { scrollProgress, iconOpacity, uiState } = options;

    const searchBar = useSearchBarStore();
    const lookupMode = useLookupMode();
    const wordlistMode = useWordlistMode();
    const content = useContentStore();
    const historyStore = useHistoryStore();
    const loading = useLoadingStore();

    // ── v-model computed bindings ──────────────────────────────────────

    const searchQuery = computed({
        get: () => searchBar.searchQuery,
        set: (value: string) => searchBar.setQuery(value),
    });

    const searchSelectedIndex = computed({
        get: () => searchBar.searchSelectedIndex,
        set: (value: number) => searchBar.setSelectedIndex(value),
    });

    // Unified results: merge lookup and wordlist results into one array
    const unifiedResults = computed(() => {
        const mode = searchBar.searchMode;
        if (mode === 'wordlist') {
            // Wordlist results already have search metadata from enriched backend
            return (searchBar.getResults('wordlist') as any[]) || [];
        }
        return (searchBar.currentResults || []) as any[];
    });

    // Computed properties for v-model bindings with mode stores directly
    const selectedSources = computed({
        get: () => Array.from(lookupMode.selectedSources) as string[],
        set: (value: string[]) => lookupMode.setSources(value as any),
    });

    const selectedLanguages = computed({
        get: () => Array.from(lookupMode.selectedLanguages) as string[],
        set: (value: string[]) => lookupMode.setLanguages(value as any),
    });

    const noAI = computed({
        get: () => lookupMode.noAI,
        set: (value: boolean) => lookupMode.setAI(!value),
    });

    // Computed properties for v-model bindings with wordlist mode store
    const wordlistFilters = computed({
        get: () => ({ ...wordlistMode.wordlistFilters }),
        set: (value: any) => wordlistMode.setWordlistFilters(value),
    });

    const wordlistSortCriteria = computed({
        get: () => [...wordlistMode.wordlistSortCriteria],
        set: (value: any) => wordlistMode.setWordlistSortCriteria(value),
    });

    // ── Derived computeds ─────────────────────────────────────────────

    const canToggleMode = computed(() => {
        // Disable mode toggle in wordlist mode
        if (searchBar.searchMode === 'wordlist') return false;

        const hasWordQuery = !!content.currentEntry;
        const hasSuggestionQuery = !!content.wordSuggestions;

        if (!hasWordQuery && !hasSuggestionQuery) return false;
        if (hasSuggestionQuery && !hasWordQuery) return false;

        // Only allow thesaurus toggle if a dedicated thesaurus response exists
        if (!content.currentThesaurus) return false;

        return true;
    });

    const placeholder = computed(() => {
        // Hide placeholder when scrolled
        if (scrollProgress() > 0.3) {
            return '';
        }

        // First check searchMode for specific modes
        if (searchBar.searchMode === 'wordlist') {
            return 'words';
        } else if (searchBar.searchMode === 'stage') {
            return 'staging';
        }

        // Default to mode-based placeholders for lookup mode
        return searchBar.getSubMode('lookup') === 'dictionary'
            ? 'definitions'
            : 'synonyms';
    });

    // Progress bar state - computed based on loading state
    const isLoadingInProgress = computed(() => {
        return (
            loading.isSearching.value ||
            (loading.loadingProgress.value > 0 &&
                loading.loadingProgress.value < 100)
        );
    });

    const showProgressBar = computed(() => {
        // Show progress bar if loading is in progress and modal is not visible
        return isLoadingInProgress.value && !loading.showLoadingModal.value;
    });

    // ── Search field layout ───────────────────────────────────────────

    const searchFieldLayout = computed(() => {
        const hasLeadingInset = iconOpacity.value > 0.1;
        const trailingActionsVisible =
            searchQuery.value.length > 0 || searchBar.isAIQuery;

        return {
            padStart: hasLeadingInset ? '1rem' : '1.5rem',
            padEnd: trailingActionsVisible
                ? searchBar.isAIQuery && searchQuery.value.length > 0
                    ? '4.25rem'
                    : '3rem'
                : uiState.expandButtonVisible
                  ? '3rem'
                  : hasLeadingInset
                    ? '1rem'
                    : '1.5rem',
            slotSize: '2rem',
            hamburgerWidth: hasLeadingInset ? '2.5rem' : '0rem',
            hamburgerGap: hasLeadingInset ? '0.5rem' : '0rem',
        };
    });

    const searchBarShellStyle = computed(
        () =>
            ({
                height: searchBar.isAIQuery
                    ? 'auto'
                    : `${uiState.searchBarHeight}px`,
                minHeight: `${uiState.searchBarHeight}px`,
                maxHeight: searchBar.isAIQuery
                    ? 'var(--search-max-h, min(26rem, 60svh))'
                    : undefined,
                borderColor:
                    searchBar.isAIQuery && !searchBar.hasErrorAnimation
                        ? 'var(--ai-accent)'
                        : searchBar.hasErrorAnimation
                          ? 'var(--error-accent)'
                          : undefined,
                '--search-pad-start': searchFieldLayout.value.padStart,
                '--search-pad-end': searchFieldLayout.value.padEnd,
                '--search-line-height': '1.1',
                '--search-line-box': '1.1em',
                '--search-text-pad-y':
                    'calc((var(--search-min-h) - var(--search-line-box)) / 2)',
                '--search-min-h': `${uiState.searchBarHeight}px`,
                '--search-max-h': searchBar.isAIQuery
                    ? 'min(26rem, 60svh)'
                    : '12.5rem',
                '--search-slot-size': searchFieldLayout.value.slotSize,
                '--search-hamburger-width':
                    searchFieldLayout.value.hamburgerWidth,
                '--search-hamburger-gap': searchFieldLayout.value.hamburgerGap,
            }) as Record<string, string | undefined>
    );

    // ── Mode-switching lifecycle ──────────────────────────────────────

    const aiQueryDetection = useAIQueryDetection();
    const semanticPoller = useSemanticStatusPoller();

    if (searchBar.searchMode === 'lookup') {
        aiQueryDetection.start();
        semanticPoller.start();
    }

    // Restart/stop when the search mode changes
    watch(
        () => searchBar.searchMode,
        (newMode, oldMode) => {
            if (newMode === oldMode) return;
            if (newMode === 'lookup') {
                aiQueryDetection.start();
                semanticPoller.start();
            } else {
                aiQueryDetection.stop();
                semanticPoller.stop();
            }
        }
    );

    // Keep the wordlist store's active query in sync with the shared search bar
    // so switching modes restores the same text and results state consistently.
    watch(
        [() => searchBar.searchMode, () => searchBar.searchQuery],
        ([mode, query]) => {
            if (mode === 'wordlist') {
                wordlistMode.setCurrentQuery(query);
            }
        },
        { immediate: true }
    );

    // ── Result index watchEffect ─────────────────────────────────────

    watchEffect(() => {
        const results = searchBar.currentResults || [];

        // Reset selected index if out of bounds
        const maxResults =
            searchBar.searchMode === 'wordlist'
                ? Math.min(10, results.length)
                : results.length;
        if (searchBar.searchSelectedIndex >= maxResults) {
            searchBar.setSelectedIndex(0);
        }
    });

    // ── Dropdown focus watchEffect ───────────────────────────────────

    watchEffect(() => {
        const focused = searchBar.isFocused;
        const query = searchBar.searchQuery;

        if (!focused) {
            if (searchBar.showDropdown) {
                searchBar.hideDropdown();
            }
        } else if (!query || query.length === 0) {
            // Show dropdown for recent searches when focused with empty query
            if (historyStore.recentSearches.length > 0) {
                searchBar.openDropdown();
            } else if (searchBar.showDropdown) {
                searchBar.hideDropdown();
            }
        }
    });

    // ── Cleanup helpers ──────────────────────────────────────────────

    function stopLifecycleEffects() {
        aiQueryDetection.stop();
        semanticPoller.stop();
    }

    return {
        // v-model bindings
        searchQuery,
        searchSelectedIndex,
        unifiedResults,
        selectedSources,
        selectedLanguages,
        noAI,
        wordlistFilters,
        wordlistSortCriteria,

        // Derived computeds
        canToggleMode,
        placeholder,
        isLoadingInProgress,
        showProgressBar,

        // Layout
        searchFieldLayout,
        searchBarShellStyle,

        // Cleanup
        stopLifecycleEffects,
    };
}
