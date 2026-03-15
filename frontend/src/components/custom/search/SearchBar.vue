<template>
    <div
        ref="searchContainer"
        :class="[
            'search-container relative z-30 mx-auto w-full origin-top px-1 sm:px-0',
            props.className,
        ]"
        :style="containerStyle"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave"
        @mousedown="handleSearchAreaInteraction"
        @click="handleSearchAreaInteraction"
    >
        <!-- Main Layout -->
        <div
            class="pointer-events-auto relative overflow-visible px-0 pt-2 pb-0 sm:px-2"
        >
            <!-- Search Bar -->
            <div
                ref="searchBarElement"
                :class="[
                    'search-bar relative flex items-center gap-2 overflow-visible px-1 py-0.5 sm:px-1',
                    'cartoon-shadow-sm rounded-2xl transition-all duration-500 ease-out',
                    searchBar.isAIQuery && !searchBar.hasErrorAnimation
                        ? 'border-2 border-amber-500 bg-amber-50 backdrop-blur-sm dark:border-amber-700/40 dark:bg-amber-950/30'
                        : searchBar.hasErrorAnimation
                          ? 'border-2 border-red-400/50 bg-gradient-to-br from-red-50/20 to-red-50/10 dark:border-red-600/50 dark:from-red-900/20 dark:to-red-900/10'
                          : 'border-2 border-border bg-background backdrop-blur-xl',
                    {
                        'cartoon-shadow-sm-hover': uiState.isContainerHovered,
                        'bg-background':
                            uiState.isContainerHovered && !searchBar.isAIQuery,
                        'shake-error': searchBar.hasErrorAnimation,
                    },
                ]"
                :style="{
                    height: searchBar.isAIQuery
                        ? 'auto'
                        : `${uiState.searchBarHeight}px`,
                    minHeight: searchBar.isAIQuery
                        ? `${uiState.searchBarHeight}px`
                        : undefined,
                    maxHeight: searchBar.isAIQuery
                        ? 'min(420px, 60vh)'
                        : undefined,
                    overflowY: searchBar.isAIQuery ? 'visible' : 'visible',
                    borderColor:
                        searchBar.isAIQuery && !searchBar.hasErrorAnimation
                            ? 'var(--ai-accent)'
                            : searchBar.hasErrorAnimation
                              ? 'var(--error-accent)'
                              : undefined,
                }"
            >
                <!-- Border shimmer overlay in AI mode -->
                <BorderShimmer
                    v-if="searchBar.isAIQuery && !searchBar.hasErrorAnimation"
                    :active="true"
                    color="var(--ai-accent)"
                    :thickness="3"
                    :border-width="2"
                    :duration="2400"
                />
                <!-- Sparkle Indicator -->
                <SparkleIndicator :show="searchBar.showSparkle" />

                <!-- Mode Toggle -->
                <ModeToggle
                    :model-value="searchBar.getSubMode('lookup') as any"
                    :can-toggle="canToggleMode"
                    :opacity="iconOpacity"
                    :show-subscript="canToggleMode"
                    :ai-mode="searchBar.isAIQuery"
                    @update:model-value="
                        (value: any) => searchBar.setSubMode('lookup', value)
                    "
                />

                <!-- Search Input Container with Autocomplete -->
                <div class="relative max-w-none min-w-0 flex-1 flex-grow">
                    <!-- Autocomplete Overlay -->
                    <AutocompleteOverlay
                        :query="searchQuery"
                        :suggestion="searchBar.autocompleteText"
                        :padding-left="iconOpacity > 0.1 ? '1rem' : '1.5rem'"
                        :padding-right="
                            searchQuery.length > 0
                                ? '5rem'
                                : uiState.expandButtonVisible
                                  ? '3rem'
                                  : iconOpacity > 0.1
                                    ? '1rem'
                                    : '1.5rem'
                        "
                        :text-align="
                            iconOpacity < 0.3 && !searchBar.isAIQuery
                                ? 'center'
                                : 'left'
                        "
                    />

                    <!-- Main Search Input -->
                    <SearchInput
                        ref="searchInputComponent"
                        v-model="searchQuery"
                        :placeholder="placeholder"
                        :ai-mode="searchBar.isAIQuery"
                        :text-align="
                            iconOpacity < 0.3 && !searchBar.isAIQuery
                                ? 'center'
                                : 'left'
                        "
                        :style="{
                            paddingLeft: iconOpacity > 0.1 ? '1rem' : '1.5rem',
                            paddingRight:
                                searchQuery.length > 0 && searchBar.isAIQuery
                                    ? '4.5rem' // Both clear and expand buttons visible
                                    : searchQuery.length > 0 ||
                                        searchBar.isAIQuery
                                      ? '3rem' // Either clear or expand button visible
                                      : iconOpacity > 0.1
                                        ? '1rem'
                                        : '1.5rem',
                            paddingTop: '0.75rem',
                            paddingBottom: '0.75rem',
                        }"
                        @enter="handleEnterWrapped"
                        @tab="acceptAutocomplete"
                        @space="handleSpaceKey"
                        @arrow-down="navigateResults(1)"
                        @arrow-up="navigateResults(-1)"
                        @arrow-left="handleArrowKey"
                        @arrow-right="handleArrowKey"
                        @escape="handleEscape"
                        @focus="handleFocus"
                        @blur="handleBlur"
                        @input-click="handleInputClick"
                    />

                    <!-- Clear/Expand Action Buttons -->
                    <SearchInputActions
                        :ai-mode="searchBar.isAIQuery"
                        :show-clear="
                            searchQuery.length > 0 && searchBar.isFocused
                        "
                        :scroll-progress="props.scrollProgress"
                        @expand="handleExpandClick"
                        @clear="clearQuery"
                    />
                </div>

                <!-- Hamburger Button -->
                <div
                    class="flex flex-shrink-0 items-center justify-center overflow-hidden transition-all duration-300 ease-out"
                    :style="{
                        opacity: iconOpacity,
                        transform: `scale(${0.9 + iconOpacity * 0.1})`,
                        pointerEvents: iconOpacity > 0.1 ? 'auto' : 'none',
                        width: iconOpacity > 0.1 ? '40px' : '0px',
                        marginLeft: iconOpacity > 0.1 ? '8px' : '0px',
                    }"
                >
                    <HamburgerIcon
                        :is-open="searchBar.showSearchControls"
                        :ai-mode="searchBar.isAIQuery"
                        @toggle="toggleControls"
                        @mousedown.prevent
                    />
                </div>
            </div>

            <!-- Thin Loading Progress Bar -->
            <ThinLoadingProgress
                :show="showProgressBar"
                :progress="loading.loadingProgress.value"
                :current-stage="loading.loadingStage.value"
                :mode="searchBar.searchMode"
                :category="loading.loadingCategory.value"
                @click="handleProgressBarClick"
            />

            <!-- Dropdowns Container -->
            <div class="absolute top-full right-0 left-0 z-40 pt-2">
                <!-- Controls Dropdown — grid-based height transition wrapper -->
                <div
                    :class="[
                        'controls-dropdown-wrapper',
                        searchBar.showSearchControls
                            ? 'controls-dropdown-open'
                            : 'controls-dropdown-closed',
                    ]"
                >
                    <SearchControls
                        class="min-h-0 overflow-hidden"
                        :show="true"
                        v-model:selected-sources="selectedSources"
                        v-model:selected-languages="selectedLanguages"
                        v-model:no-a-i="noAI"
                        v-model:wordlist-filters="wordlistFilters"
                        :wordlist-sort-criteria="wordlistSortCriteria"
                        @update:wordlist-sort-criteria="
                            (value: any) => (wordlistSortCriteria = value)
                        "
                        :ai-suggestions="searchBar.aiSuggestions as string[]"
                        :is-development="uiState.isDevelopment"
                        :show-refresh-button="
                            !!content.currentEntry &&
                            searchBar.searchMode === 'lookup'
                        "
                        :force-refresh-mode="loading.forceRefreshMode.value"
                        @word-select="selectWord"
                        @clear-storage="clearAllStorage"
                        @interaction="handleSearchAreaInteraction"
                        @toggle-sidebar="ui.toggleSidebar()"
                        @toggle-refresh="handleForceRegenerate"
                        @execute-search="handleEnterWrapped"
                    />
                </div>

                <!-- Search Results Container -->
                <div>
                    <SearchResults
                        ref="searchResultsComponent"
                        :show="searchBar.showDropdown"
                        :results="(searchBar.currentResults || []) as any[]"
                        :loading="loading.isSearching.value"
                        v-model:selected-index="searchSelectedIndex"
                        :query="searchQuery"
                        :ai-mode="searchBar.isAIQuery"
                        :wordlist-mode="searchBar.searchMode === 'wordlist'"
                        :wordlist-results="
                            (searchBar.getResults('wordlist') as any[]) || []
                        "
                        :recent-searches="historyStore.recentSearches as any[]"
                        @select-result="selectResult"
                        @interaction="handleSearchAreaInteraction"
                    />
                </div>
            </div>
        </div>
    </div>

    <!-- Expanded Input Modal -->
    <ExpandModal
        :show="uiState.showExpandModal"
        :initial-query="searchQuery"
        @close="closeExpandModal"
        @submit="submitExpandedQuery"
    />

    <ConfirmDialog
        v-model:open="showClearStorageDialog"
        title="Clear All Storage"
        description="This will clear all local storage including history and settings."
        message="This action cannot be undone. You will lose all your saved settings and search history."
        confirm-text="Clear All"
        cancel-text="Cancel"
        :destructive="true"
        @confirm="confirmClearStorage"
    />
</template>

<script setup lang="ts">
import { ref, computed, watch, watchEffect, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
// Modular stores - direct imports
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useContentStore } from '@/stores/content/content';
import { useHistoryStore } from '@/stores/content/history';
import { useUIStore } from '@/stores/ui/ui-state';
import { useLoadingStore } from '@/stores/ui/loading';
// Maximize2 and X moved to SearchInputActions component
import { HamburgerIcon } from '@/components/custom/icons';
import { BorderShimmer } from '@/components/custom/animation';

// Import components
import SearchInput from './components/SearchInput.vue';
import SparkleIndicator from './components/SparkleIndicator.vue';
import ModeToggle from './components/ModeToggle.vue';
import AutocompleteOverlay from './components/AutocompleteOverlay.vue';
import SearchControls from './components/SearchControls.vue';
import SearchResults from './components/SearchResults.vue';
import ExpandModal from './components/ExpandModal.vue';
import ThinLoadingProgress from './components/ThinLoadingProgress.vue';
import SearchInputActions from './components/SearchInputActions.vue';
import ConfirmDialog from '../ConfirmDialog.vue';

// Import composables
import {
    useSearchBarUI,
    useSearchBarNavigation,
    useFocusManagement,
    useModalManagement,
    useSearchBarScroll,
    useAutocomplete,
    useAIQueryDetection,
    useSemanticStatusPoller,
} from './composables';

interface SearchBarProps {
    className?: string;
    hideDelay?: number;
    scrollThreshold?: number;
    scrollY?: number;
    shrinkPercentage?: number;
    scrollProgress?: number;
}

const props = withDefaults(defineProps<SearchBarProps>(), {
    hideDelay: 3000,
    scrollThreshold: 100,
    scrollY: 0,
    shrinkPercentage: 0,
    scrollProgress: 0,
});

const emit = defineEmits<{
    focus: [];
    blur: [];
    mouseenter: [];
    mouseleave: [];
    'stage-enter': [query: string];
}>();

// Store & State - Direct store access for single source of truth
const searchBar = useSearchBarStore();
const lookupMode = useLookupMode();
const wordlistMode = useWordlistMode();
const content = useContentStore();
const historyStore = useHistoryStore();
const ui = useUIStore();
const loading = useLoadingStore();
const router = useRouter();
const { iconOpacity, uiState } = useSearchBarUI();

// All functionality now uses modular stores directly - no reactive wrapper needed

// Computed properties from stores
const canToggleMode = computed(() => {
    // Disable mode toggle in wordlist mode
    if (searchBar.searchMode === 'wordlist') return false;

    const hasWordQuery = !!content.currentEntry;
    const hasSuggestionQuery = !!content.wordSuggestions;

    if (!hasWordQuery && !hasSuggestionQuery) return false;
    if (hasSuggestionQuery && !hasWordQuery) return false;
    return true;
});

const placeholder = computed(() => {
    // Hide placeholder when scrolled
    if (props.scrollProgress > 0.3) {
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

// Results container style — controls wrapper handles its own spacing now

// Computed properties for v-model bindings
const searchQuery = computed({
    get: () => searchBar.searchQuery,
    set: (value: string) => searchBar.setQuery(value),
});

const searchSelectedIndex = computed({
    get: () => searchBar.searchSelectedIndex,
    set: (value: number) => searchBar.setSelectedIndex(value),
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

// Progress bar state - computed based on loading state
const isLoadingInProgress = computed(() => {
    return (
        loading.isSearching.value ||
        (loading.loadingProgress.value > 0 &&
            loading.loadingProgress.value < 100)
    );
});

// Dialog state
const showClearStorageDialog = ref(false);

const showProgressBar = computed(() => {
    // Show progress bar if loading is in progress and modal is not visible
    return isLoadingInProgress.value && !loading.showLoadingModal.value;
});

// Refs
const searchContainer = ref<HTMLDivElement>();
const searchBarElement = ref<HTMLDivElement>();
void searchBarElement; // bound via template ref="searchBarElement"
const searchInputComponent = ref<any>();
const searchResultsComponent = ref<any>();

// Computed ref for search input element
const searchInputRef = computed(() => searchInputComponent.value?.element);

// Scroll animation setup - use props for scroll data
const { containerStyle } = useSearchBarScroll({
    shrinkPercentage: () => props.shrinkPercentage,
});

// Autocomplete setup
const {
    autocompleteText,
    updateAutocomplete,
    acceptAutocomplete,
    handleSpaceKey: handleAutocompleteSpaceKey,
    handleArrowKey: handleAutocompleteArrowKey,
    handleInputClick: handleAutocompleteInputClick,
} = useAutocomplete({
    query: computed(() => searchBar.searchQuery),
    searchResults: computed(() => {
        // Use appropriate results based on search mode
        if (searchBar.searchMode === 'wordlist') {
            return (
                (searchBar.getResults('wordlist')?.slice(0, 10) as any) || []
            );
        }
        return (searchBar.getResults('lookup') as any) || [];
    }),
    searchInput: searchInputRef,
    onQueryUpdate: (newQuery: string) => {
        searchBar.setQuery(newQuery);
    },
});

// Search operations - use orchestrator
import { useSearchOrchestrator } from './composables/useSearchOrchestrator';
const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBar.searchQuery),
});
const { performSearch, clearSearch, cleanup: cleanupSearch } = orchestrator;

// AI query detection and semantic status poller (extracted from lookup store)
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

// Unified navigation and keyboard handling
const {
    navigateResults,
    handleEnter,
    handleEscape,
    selectResult,
    handleSpaceKey,
    handleArrowKey,
} = useSearchBarNavigation({
    searchInputRef,
    searchResultsComponent,
    onAutocompleteAccept: acceptAutocomplete,
    onAutocompleteSpace: handleAutocompleteSpaceKey,
    onAutocompleteArrow: handleAutocompleteArrowKey,
});

// Focus management
const {
    handleFocus,
    handleBlur,
    handleSearchAreaInteraction,
    focusInput,
    cleanup: cleanupFocus,
} = useFocusManagement({
    searchInputComponent,
    searchContainer,
    emit: emit as (event: string, ...args: any[]) => void,
});

// Modal management
const {
    handleExpandClick,
    closeExpandModal,
    submitExpandedQuery: submitExpandedQueryBase,
} = useModalManagement();

// Event Handlers
const handleMouseEnter = () => {
    uiState.isContainerHovered = true;
    emit('mouseenter');
};

const handleMouseLeave = () => {
    uiState.isContainerHovered = false;
    emit('mouseleave');
};

const handleInputClick = (event: MouseEvent) => {
    handleSearchAreaInteraction();
    handleAutocompleteInputClick(event);
};

// Override handleEnter to handle stage mode
const handleEnterWrapped = async () => {
    if (searchBar.searchMode === 'stage' && searchBar.searchQuery) {
        emit('stage-enter', searchBar.searchQuery);
        return;
    }
    await handleEnter();
};

const toggleControls = () => {
    searchBar.toggleSearchControls();
};

const selectWord = (word: string) => {
    searchBar.hideDropdown();
    searchBar.hideControls();
    searchBar.clearResults();
    // Navigate — the route watcher in Home.vue handles the fetch
    const subMode = searchBar.getSubMode('lookup');
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word } });
};

const handleForceRegenerate = () => {
    handleSearchAreaInteraction();
    loading.setForceRefreshMode(!loading.forceRefreshMode.value);
};

const handleProgressBarClick = () => {
    // Reshow the loading progress modal when clicking the thin progress bar
    loading.setShowLoadingModal(true);
};

const clearQuery = () => {
    clearSearch();
    focusInput();
};

const clearAllStorage = () => {
    showClearStorageDialog.value = true;
};

const confirmClearStorage = () => {
    localStorage.clear();
    sessionStorage.clear();
    showClearStorageDialog.value = false;
    window.location.reload();
};

// Expand modal wrapper
const submitExpandedQuery = (query: string) => {
    searchBar.setQuery(query);
    submitExpandedQueryBase(query, handleEnterWrapped);
};

// Modal state is now handled directly by useModalManagement composable
// No watchers needed - single source of truth

// Autocomplete updates are now handled by the useAutocomplete composable
// which already watches query and results internally

// Scroll state updates are handled by useSearchBarScroll composable
// which already computes based on props

// Close dropdown when loading modal appears (lookup initiated)
watch(
    () => loading.showLoadingModal.value,
    (showModal) => {
        if (showModal && searchBar.showDropdown) {
            searchBar.hideDropdown();
        }
    }
);

// Reset selected index when results change
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

// Click outside handler is now in useFocusManagement composable

// Watch query changes for immediate search - NO DEBOUNCING
watch(
    () => searchBar.searchQuery,
    () => {
        // Trigger search immediately for all modes
        performSearch();

        // Immediately recompute autocomplete for the new query.
        // This clears stale suggestions right away (e.g. if the new query
        // no longer matches the old suggestion prefix).
        updateAutocomplete();
        searchBar.setAutocompleteText(autocompleteText.value);
    }
);

// Watch search results for autocomplete updates.
// Use a single watcher on currentResults (covers both lookup and wordlist modes)
// instead of only watching lookup results.
watch(
    () => searchBar.currentResults,
    () => {
        updateAutocomplete();
        searchBar.setAutocompleteText(autocompleteText.value);
    }
);

// Hide dropdown when focus is lost; show recent searches on empty focus
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

// Initialize
onMounted(() => {
    searchBar.setAISuggestions([]);
});

// Cleanup
onUnmounted(() => {
    cleanupSearch();
    cleanupFocus();
    aiQueryDetection.stop();
    semanticPoller.stop();
});
</script>

<style scoped>
/*
 * Controls dropdown: grid-based height animation.
 * Uses grid-template-rows 0fr/1fr for smooth collapse without max-height.
 */
.controls-dropdown-wrapper {
    display: grid;
    will-change: grid-template-rows, opacity;
}

.controls-dropdown-open {
    grid-template-rows: 1fr;
    opacity: 1;
    margin-bottom: 0.5rem;
    /* ease-apple-smooth: cubic-bezier(0.4, 0, 0.2, 1) */
    transition:
        grid-template-rows 250ms cubic-bezier(0.4, 0, 0.2, 1),
        opacity 150ms cubic-bezier(0, 0, 0.2, 1),
        margin-bottom 250ms cubic-bezier(0.4, 0, 0.2, 1);
}

.controls-dropdown-closed {
    grid-template-rows: 0fr;
    opacity: 0;
    margin-bottom: 0;
    transition:
        grid-template-rows 180ms cubic-bezier(0.4, 0, 1, 1),
        opacity 120ms cubic-bezier(0.4, 0, 1, 1) 30ms,
        margin-bottom 180ms cubic-bezier(0.4, 0, 1, 1);
}

/* Disable animations for reduced motion */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
    }
}
</style>
