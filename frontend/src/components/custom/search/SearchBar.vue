<template>
    <div
        ref="searchContainer"
        :class="[
            'search-container relative z-bar mx-auto w-full origin-top px-1 sm:px-2',
            props.className,
        ]"
        :style="containerStyle"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave"
        @mousedown="handleSearchAreaInteraction"
        @click="handleSearchAreaInteraction"
    >
        <!-- Main Layout -->
        <div class="pointer-events-auto relative overflow-visible pt-2 pb-0">
            <!-- Search Bar Shell -->
            <SearchBarShell
                ref="shellComponent"
                v-model:query="searchQuery"
                :icon-opacity="iconOpacity"
                :container-hovered="uiState.isContainerHovered"
                :shell-style="searchBarShellStyle"
                :can-toggle-mode="canToggleMode"
                :placeholder="placeholder"
                :scroll-progress="props.scrollProgress"
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
                @expand="handleExpandClick"
                @clear="clearQuery"
                @toggle-controls="toggleControls"
            />

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
            <SearchBarDropdowns
                ref="dropdownsComponent"
                v-model:selected-sources="selectedSources"
                v-model:selected-languages="selectedLanguages"
                v-model:no-a-i="noAI"
                v-model:wordlist-filters="wordlistFilters"
                v-model:wordlist-sort-criteria="wordlistSortCriteria"
                v-model:selected-index="searchSelectedIndex"
                :is-development="uiState.isDevelopment"
                :show-refresh-button="!!content.currentEntry && searchBar.searchMode === 'lookup'"
                :force-refresh-mode="loading.forceRefreshMode.value"
                :results="unifiedResults"
                :is-searching="loading.isSearching.value"
                :query="searchQuery"
                :recent-searches="historyStore.recentSearches as any[]"
                @word-select="selectWord"
                @clear-storage="clearAllStorage"
                @interaction="handleSearchAreaInteraction"
                @toggle-sidebar="ui.toggleSidebar()"
                @toggle-refresh="handleForceRegenerate"
                @execute-search="handleEnterWrapped"
                @select-result="selectResult"
            />
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
        description="This will clear all local storage including history and settings. This action cannot be undone."
        confirm-label="Clear All"
        :destructive="true"
        @confirm="confirmClearStorage"
    />
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useContentStore } from '@/stores/content/content';
import { useHistoryStore } from '@/stores/content/history';
import { useUIStore } from '@/stores/ui/ui-state';
import { useLoadingStore } from '@/stores/ui/loading';
import { ConfirmDialog } from '@mkbabb/glass-ui';

// Sub-components
import SearchBarShell from './components/SearchBarShell.vue';
import SearchBarDropdowns from './components/SearchBarDropdowns.vue';
import ExpandModal from './components/ExpandModal.vue';
import ThinLoadingProgress from './components/ThinLoadingProgress.vue';

// Composables
import {
    useSearchBarUI,
    useSearchBarBindings,
    useSearchBarNavigation,
    useFocusManagement,
    useModalManagement,
    useSearchBarScroll,
    useAutocomplete,
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

// Stores
const searchBar = useSearchBarStore();
const content = useContentStore();
const historyStore = useHistoryStore();
const ui = useUIStore();
const loading = useLoadingStore();
const router = useRouter();
const { iconOpacity, uiState } = useSearchBarUI();

// Bindings (v-model bridges, computeds, mode-lifecycle watchers)
const {
    searchQuery,
    searchSelectedIndex,
    unifiedResults,
    selectedSources,
    selectedLanguages,
    noAI,
    wordlistFilters,
    wordlistSortCriteria,
    canToggleMode,
    placeholder,
    showProgressBar,
    searchBarShellStyle,
    stopLifecycleEffects,
} = useSearchBarBindings({
    scrollProgress: () => props.scrollProgress,
    iconOpacity,
    uiState,
});

// Refs
const showClearStorageDialog = ref(false);
const searchContainer = ref<HTMLDivElement>();
const shellComponent = ref<InstanceType<typeof SearchBarShell>>();
const dropdownsComponent = ref<InstanceType<typeof SearchBarDropdowns>>();

// Derived refs from sub-components
const searchInputComponent = computed(() => shellComponent.value?.searchInputElement);
const searchInputRef = computed(() => searchInputComponent.value?.element);
const searchResultsComponent = computed(() => dropdownsComponent.value?.searchResultsComponent);

// Scroll animation
const { containerStyle } = useSearchBarScroll({
    shrinkPercentage: () => props.shrinkPercentage,
});

// Autocomplete
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
        if (searchBar.searchMode === 'wordlist') {
            return (searchBar.getResults('wordlist')?.slice(0, 10) as any) || [];
        }
        return (searchBar.getResults('lookup') as any) || [];
    }),
    searchInput: searchInputRef,
    onQueryUpdate: (newQuery: string) => {
        searchBar.setQuery(newQuery);
    },
});

// Search orchestrator
import { useSearchOrchestrator } from './composables/useSearchOrchestrator';
const { performSearch, clearSearch, cleanup: cleanupSearch } = useSearchOrchestrator({
    query: computed(() => searchBar.searchQuery),
});

// Keyboard navigation
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

const handleEnterWrapped = async () => {
    if (searchBar.searchMode === 'stage' && searchBar.searchQuery) {
        emit('stage-enter', searchBar.searchQuery);
        return;
    }
    await handleEnter();
};

const toggleControls = () => searchBar.toggleSearchControls();

const selectWord = (word: string) => {
    searchBar.hideDropdown();
    searchBar.hideControls();
    searchBar.clearResults();
    const subMode = searchBar.getSubMode('lookup');
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word } });
};

const handleForceRegenerate = () => {
    handleSearchAreaInteraction();
    loading.setForceRefreshMode(!loading.forceRefreshMode.value);
};

const handleProgressBarClick = () => loading.setShowLoadingModal(true);
const clearQuery = () => { clearSearch(); focusInput(); };
const clearAllStorage = () => { showClearStorageDialog.value = true; };

const confirmClearStorage = () => {
    localStorage.clear();
    sessionStorage.clear();
    showClearStorageDialog.value = false;
    window.location.reload();
};

const submitExpandedQuery = (query: string) => {
    searchBar.setQuery(query);
    submitExpandedQueryBase(query, handleEnterWrapped);
};

// Watchers
watch(() => loading.showLoadingModal.value, (showModal) => {
    if (showModal && searchBar.showDropdown) searchBar.hideDropdown();
});

watch(() => searchBar.searchQuery, () => {
    performSearch();
    updateAutocomplete();
    searchBar.setAutocompleteText(autocompleteText.value);
});

watch(() => searchBar.currentResults, () => {
    updateAutocomplete();
    searchBar.setAutocompleteText(autocompleteText.value);
});

onMounted(() => searchBar.setAISuggestions([]));

onUnmounted(() => {
    cleanupSearch();
    cleanupFocus();
    stopLifecycleEffects();
});
</script>

<style scoped>
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
    }
}
</style>
