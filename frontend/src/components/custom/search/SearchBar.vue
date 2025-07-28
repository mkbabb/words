<template>
    <div
        ref="searchContainer"
        :class="[
            'search-container relative z-50 mx-auto w-full origin-top px-1 sm:px-0',
            props.className,
        ]"
        :style="containerStyle"
        @mouseenter="handleMouseEnter"
        @mouseleave="handleMouseLeave"
    >
        <!-- Main Layout -->
        <div class="pointer-events-auto relative overflow-visible pt-2 px-0 sm:px-2 pb-0">
            <!-- Search Bar -->
            <div
                ref="searchBarElement"
                :class="[
                    'search-bar relative flex items-center gap-2 overflow-visible px-1 sm:px-1 py-0.5',
                    'cartoon-shadow-sm rounded-2xl transition-all duration-500 ease-out',
                    state.isAIQuery && !state.showErrorAnimation
                        ? 'border-2 border-amber-500 dark:border-amber-700/40 bg-amber-50 dark:bg-amber-950/30 backdrop-blur-sm'
                        : state.showErrorAnimation
                        ? 'border-2 border-red-400/50 dark:border-red-600/50 bg-gradient-to-br from-red-50/20 to-red-50/10 dark:from-red-900/20 dark:to-red-900/10'
                        : 'border-2 border-border bg-background/20 backdrop-blur-3xl',
                    {
                        'cartoon-shadow-sm-hover': state.isContainerHovered,
                        'bg-background/30':
                            state.isContainerHovered && !state.isAIQuery,
                        'shake-error': state.showErrorAnimation,
                    },
                ]"
                :style="{
                    height: state.isAIQuery
                        ? 'auto'
                        : `${state.searchBarHeight}px`,
                    minHeight: state.isAIQuery
                        ? `${state.searchBarHeight}px`
                        : undefined,
                    maxHeight: state.isAIQuery
                        ? '420px'
                        : undefined,
                    overflowY: state.isAIQuery
                        ? 'visible'
                        : 'visible',
                    borderColor: state.isAIQuery && !state.showErrorAnimation
                        ? '#fbbf24'
                        : state.showErrorAnimation
                        ? '#f87171'
                        : undefined,
                }"
            >
                <!-- Sparkle Indicator -->
                <SparkleIndicator :show="state.showSparkle" />

                <!-- Mode Toggle -->
                <ModeToggle
                    v-model="state.mode"
                    :can-toggle="canToggleMode"
                    :opacity="iconOpacity"
                    :ai-mode="state.isAIQuery"
                />

                <!-- Search Input Container with Autocomplete -->
                <div class="relative max-w-none min-w-0 flex-1 flex-grow">
                    <!-- Autocomplete Overlay -->
                    <AutocompleteOverlay
                        :query="state.query"
                        :suggestion="state.autocompleteText"
                        :padding-left="iconOpacity > 0.1 ? '1rem' : '1.5rem'"
                        :padding-right="
                            state.query.length > 0
                                ? '5rem'
                                : state.expandButtonVisible
                                ? '3rem'
                                : iconOpacity > 0.1
                                  ? '1rem'
                                  : '1.5rem'
                        "
                        :text-align="
                            iconOpacity < 0.3 && !state.isAIQuery
                                ? 'center'
                                : 'left'
                        "
                    />

                    <!-- Main Search Input -->
                    <SearchInput
                        ref="searchInputComponent"
                        v-model="state.query"
                        :placeholder="placeholder"
                        :ai-mode="state.isAIQuery"
                        :text-align="
                            iconOpacity < 0.3 && !state.isAIQuery
                                ? 'center'
                                : 'left'
                        "
                        :style="{
                            paddingLeft: iconOpacity > 0.1 ? '1rem' : '1.5rem',
                            paddingRight: state.query.length > 0
                                ? '5rem'
                                : state.expandButtonVisible
                                ? '3rem'
                                : iconOpacity > 0.1
                                  ? '1rem'
                                  : '1.5rem',
                            paddingTop: '0.75rem',
                            paddingBottom: '0.75rem',
                        }"
                        @enter="handleEnter"
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

                    <!-- Clear Button -->
                    <Transition
                        enter-active-class="transition-all duration-200 ease-out"
                        leave-active-class="transition-all duration-200 ease-in"
                        enter-from-class="opacity-0 scale-90"
                        leave-to-class="opacity-0 scale-90"
                    >
                        <button
                            v-if="state.query.length > 0 && state.isFocused"
                            @click.stop="clearQuery"
                            :class="[
                                'absolute right-2 top-1/2 -translate-y-1/2 z-20 rounded-md p-1 transition-all duration-200',
                                'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
                                state.isAIQuery
                                    ? 'bg-transparent hover:bg-amber-100/80 dark:hover:bg-amber-900/40'
                                    : 'bg-transparent hover:bg-muted/80'
                            ]"
                            title="Clear search"
                        >
                            <X
                                :class="[
                                    'h-4 w-4',
                                    state.isAIQuery
                                        ? 'text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200'
                                        : 'text-foreground/50 hover:text-foreground/70'
                                ]"
                            />
                        </button>
                    </Transition>

                    <!-- Expand Button -->
                    <Transition
                        enter-active-class="transition-all duration-200 ease-out"
                        leave-active-class="transition-all duration-200 ease-in"
                        enter-from-class="opacity-0 scale-90"
                        leave-to-class="opacity-0 scale-90"
                    >
                        <button
                            v-if="state.expandButtonVisible && state.scrollProgress < 0.3 && state.query.length === 0"
                            :class="[
                                'absolute right-2 bottom-2 z-20 rounded-md p-1 transition-all duration-200',
                                'hover:scale-105 focus:ring-2 focus:ring-primary/50 focus:outline-none',
                                state.isAIQuery
                                    ? 'bg-amber-100/80 hover:bg-amber-200/80 dark:bg-amber-900/40 dark:hover:bg-amber-800/40'
                                    : 'bg-muted/50 hover:bg-muted/80'
                            ]"
                            :style="{
                                opacity: 1 - state.scrollProgress * 3,
                                transform: `scale(${1 - state.scrollProgress * 0.5})`
                            }"
                            @click.stop="handleExpandClick"
                            title="Expand for longer input"
                        >
                            <Maximize2
                                :class="[
                                    'h-4 w-4',
                                    state.isAIQuery
                                        ? 'text-amber-700 hover:text-amber-800 dark:text-amber-300 dark:hover:text-amber-200'
                                        : 'text-foreground/70 hover:text-foreground'
                                ]"
                            />
                        </button>
                    </Transition>
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
                        :is-open="state.showControls"
                        :ai-mode="state.isAIQuery"
                        @toggle="toggleControls"
                        @mousedown.prevent
                    />
                </div>

                <!-- Progress Bar -->
                <!-- <div
                    v-if="store.loadingProgress > 0"
                    class="absolute right-0 -bottom-2 left-0 h-2
                        overflow-hidden"
                >
                    <div
                        class="h-full rounded-full transition-[width]
                            duration-300"
                        :style="{
                            width: `${store.loadingProgress}%`,
                            background: generateRainbowGradient(8),
                        }"
                    />
                </div> -->
            </div>

            <!-- Dropdowns Container -->
            <div class="absolute top-full right-0 left-0 z-50 pt-2">
                <!-- Controls Dropdown -->
                <SearchControls
                    :show="state.showControls"
                    v-model:search-mode="state.searchMode"
                    v-model:selected-sources="state.selectedSources"
                    v-model:selected-languages="state.selectedLanguages"
                    v-model:no-a-i="state.noAI"
                    :ai-suggestions="state.aiSuggestions"
                    :is-development="state.isDevelopment"
                    :show-refresh-button="!!store.currentEntry && state.searchMode === 'lookup'"
                    :force-refresh-mode="state.forceRefreshMode"
                    @word-select="selectWord"
                    @clear-storage="clearAllStorage"
                    @interaction="handleSearchAreaInteraction"
                    @toggle-sidebar="store.toggleSidebar()"
                    @toggle-refresh="handleForceRegenerate"
                    @execute-search="handleEnter"
                />

                <!-- Search Results Container -->
                <div
                    :style="resultsContainerStyle"
                    class="transition-all duration-350 ease-apple-spring"
                >
                    <SearchResults
                        ref="searchResultsComponent"
                        :show="state.showResults"
                        :results="state.searchResults"
                        :loading="state.isSearching"
                        v-model:selected-index="state.selectedIndex"
                        :query="state.query"
                        :ai-mode="state.isAIQuery"
                        @select-result="selectResult"
                        @interaction="handleSearchAreaInteraction"
                    />
                </div>
            </div>
        </div>
    </div>

    <!-- Expanded Input Modal -->
    <ExpandModal
        :show="state.showExpandModal"
        :initial-query="state.query"
        @close="closeExpandModal"
        @submit="submitExpandedQuery"
    />
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useMagicKeys, whenever } from '@vueuse/core';
import { useRouter } from 'vue-router';
import { useAppStore } from '@/stores';
import type { SearchResult } from '@/types';
import { showError } from '@/plugins/toast';
import { Maximize2, X } from 'lucide-vue-next';
import { HamburgerIcon } from '@/components/custom/icons';

// Import components
import SearchInput from './components/SearchInput.vue';
import SparkleIndicator from './components/SparkleIndicator.vue';
import ModeToggle from './components/ModeToggle.vue';
import AutocompleteOverlay from './components/AutocompleteOverlay.vue';
import SearchControls from './components/SearchControls.vue';
import SearchResults from './components/SearchResults.vue';
import ExpandModal from './components/ExpandModal.vue';

// Import composables and utilities
import { useSearchBarUI } from './composables/useSearchBarUI';
import { useScrollAnimationSimple } from './composables/useScrollAnimationSimple';
import { useAutocomplete } from './composables/useAutocomplete';
import { shouldTriggerAIMode, extractWordCount } from './utils/ai-query';
import { shouldShowExpandButton } from './utils/keyboard';

interface SearchBarProps {
    className?: string;
    shrinkPercentage?: number;
    hideDelay?: number;
    scrollThreshold?: number;
}

const props = withDefaults(defineProps<SearchBarProps>(), {
    shrinkPercentage: 0,
    hideDelay: 3000,
    scrollThreshold: 100,
});

// Debug prop changes
if (import.meta.env.DEV) {
    watch(
        () => props.shrinkPercentage,
        (newVal, oldVal) => {
            if (newVal !== oldVal) {
                console.log('SearchBar prop changed:', { oldVal, newVal });
            }
        }
    );
}

const emit = defineEmits<{
    focus: [];
    blur: [];
    mouseenter: [];
    mouseleave: [];
    'stage-enter': [query: string];
}>();

// Store & State
const store = useAppStore();
const router = useRouter();
const { uiState, iconOpacity } = useSearchBarUI();

// Reactive references for template use
const state = reactive({
    // Store state (computed)
    get query() { return store.searchQuery; },
    set query(value) { store.searchQuery = value; },
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
});

const canToggleMode = computed(() => {
    const hasWordQuery = !!store.currentEntry;
    const hasSuggestionQuery = !!store.wordSuggestions;
    
    if (!hasWordQuery && !hasSuggestionQuery) return false;
    if (hasSuggestionQuery && !hasWordQuery) return false;
    return true;
});

// Refs
const searchContainer = ref<HTMLDivElement>();
const searchBarElement = ref<HTMLDivElement>();
const searchInputComponent = ref<any>();
const searchResultsComponent = ref<any>();

// Computed
const placeholder = computed(() => {
    // Hide placeholder when scrolled
    if (state.scrollProgress > 0.3) {
        return '';
    }
    
    // First check searchMode for specific modes
    if (state.searchMode === 'wordlist') {
        return 'Enter words separated by spaces or commas...';
    } else if (state.searchMode === 'stage') {
        return 'Enter text for staging...';
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

// Scroll animation setup
const { containerStyle, updateScrollState } = useScrollAnimationSimple(
    computed(() => state.scrollProgress),
    computed(() => state.isContainerHovered),
    computed(() => state.isFocused),
    computed(() => state.showControls || state.showResults)
);

// Update scroll progress from prop
watch(
    () => props.shrinkPercentage,
    (newValue) => {
        state.scrollProgress = newValue;
        // Debug logging
        if (import.meta.env.DEV) {
            console.log('SearchBar scroll update:', {
                shrinkPercentage: newValue,
                scrollProgress: state.scrollProgress,
                containerStyle: containerStyle.value,
            });
        }
    },
    { immediate: true }
);

// Create a computed ref for the search input element
const searchInputRef = computed(() => searchInputComponent.value?.element);

// Autocomplete setup
const {
    autocompleteText,
    updateAutocomplete,
    acceptAutocomplete,
    handleSpaceKey: handleAutocompleteSpaceKey,
    handleArrowKey: handleAutocompleteArrowKey,
    handleInputClick: handleAutocompleteInputClick,
} = useAutocomplete({
    query: computed(() => state.query),
    searchResults: computed(() => state.searchResults),
    searchInput: searchInputRef,
    onQueryUpdate: (newQuery: string) => {
        state.query = newQuery;
    },
});

// Timers
let searchTimer: ReturnType<typeof setTimeout> | undefined;
let isInteractingWithSearchArea = false;

// Watch query for autocomplete
watch(
    () => state.query,
    () => {
        updateAutocomplete();
        state.autocompleteText = autocompleteText.value;
        state.expandButtonVisible = shouldShowExpandButton(
            state.isAIQuery,
            state.query.length,
            state.query.includes('\n')
        );
    }
);

// Watch search results for autocomplete
watch(
    () => state.searchResults,
    () => {
        state.selectedIndex = 0;
        updateAutocomplete();
        state.autocompleteText = autocompleteText.value;
    }
);

// Event Handlers
const handleMouseEnter = () => {
    state.isContainerHovered = true;
    emit('mouseenter');
};

const handleMouseLeave = () => {
    state.isContainerHovered = false;
    emit('mouseleave');
};

const handleFocus = () => {
    state.isFocused = true;
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
        state.query.length >= 2
    ) {
        state.searchResults = store.sessionState.searchResults.slice(0, 8);
        state.showResults = true;
    }
};

const handleBlur = () => {
    setTimeout(() => {
        if (isInteractingWithSearchArea) return;

        state.isFocused = false;
        emit('blur');

        // Hide results on blur
        state.showResults = false;
        state.searchResults = [];
        state.isSearching = false;
    }, 150);
};

const handleInputClick = (event: MouseEvent) => {
    handleSearchAreaInteraction();
    handleAutocompleteInputClick(event);
};

const handleSearchAreaInteraction = () => {
    isInteractingWithSearchArea = true;
    setTimeout(() => {
        isInteractingWithSearchArea = false;
    }, 100);
};

// Search functionality
const performSearch = () => {
    clearTimeout(searchTimer);
    
    // Skip search if this is a direct lookup from sidebar/controls
    if (store.isDirectLookup) {
        state.searchResults = [];
        state.showResults = false;
        return;
    }
    
    store.searchQuery = state.query;

    if (!state.query || state.query.length < 2) {
        state.searchResults = [];
        state.showResults = false;
        state.isSearching = false;
        state.isAIQuery = false;
        state.showSparkle = false;
        return;
    }

    state.isSearching = true;

    searchTimer = setTimeout(async () => {
        try {
            const results = await store.search(state.query);
            state.searchResults = results.slice(0, 8);
            state.selectedIndex = 0;

            if (store.sessionState) {
                store.sessionState.searchResults = results;
            }

            // Show results if we have them
            state.showResults = results.length > 0;

            // Activate AI mode
            if (results.length === 0 && shouldTriggerAIMode(state.query)) {
                state.isAIQuery = true;
                state.showSparkle = true;
                store.sessionState.isAIQuery = true;
                store.sessionState.aiQueryText = state.query;
            } else {
                state.isAIQuery = false;
                state.showSparkle = false;
                store.sessionState.isAIQuery = false;
                store.sessionState.aiQueryText = '';
            }
        } catch (error) {
            console.error('Search error:', error);
            state.searchResults = [];
        } finally {
            state.isSearching = false;
        }
    }, 200);
};

// Keyboard handlers
const handleEnter = async () => {
    clearTimeout(searchTimer);

    if (state.autocompleteText) {
        const accepted = await acceptAutocomplete();
        if (accepted) {
            return;
        }
    }

    // Handle stage mode
    if (state.searchMode === 'stage' && state.query) {
        store.searchQuery = state.query;
        emit('stage-enter', state.query);
        return;
    }

    // Handle wordlist mode
    if (state.searchMode === 'wordlist' && state.query) {
        // Parse the query as a list of words (space, comma, or newline separated)
        const words = state.query
            .split(/[,\\s\\n]+/)
            .map((word) => word.trim())
            .filter((word) => word.length > 0);

        if (words.length > 0) {
            // Process wordlist - for now, just look up the first word
            // TODO: Implement full wordlist processing
            
            // Navigate to appropriate route based on mode
            const routeName = state.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
            router.push({ name: routeName, params: { word: words[0] } });
            
            // Use searchWord for direct lookup
            await store.searchWord(words[0]);

            // You could emit a wordlist event here for future handling
            // emit('wordlist-enter', words);
        }
        return;
    }

    // Handle AI query mode
    if (state.isAIQuery && state.query) {
        try {
            const extractedCount = extractWordCount(state.query);
            const wordSuggestions = await store.getAISuggestions(
                state.query,
                extractedCount
            );

            if (wordSuggestions && wordSuggestions.suggestions.length > 0) {
                store.wordSuggestions = wordSuggestions;
                state.mode = 'suggestions';
                store.hasSearched = true;
                store.sessionState.aiQueryText = state.query;
            } else {
                state.showErrorAnimation = true;
                showError('No word suggestions found for this query');
                setTimeout(() => {
                    state.showErrorAnimation = false;
                }, 600);
            }
        } catch (error: any) {
            console.error('AI suggestion error:', error);
            state.showErrorAnimation = true;
            showError(error.message || 'Failed to get word suggestions');
            setTimeout(() => {
                state.showErrorAnimation = false;
            }, 600);
        }
        return;
    }

    // Regular search
    if (state.searchResults.length > 0 && state.selectedIndex >= 0) {
        await selectResult(state.searchResults[state.selectedIndex]);
    } else if (state.query) {
        // Navigate to appropriate route based on mode
        const routeName = state.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
        router.push({ name: routeName, params: { word: state.query } });
        
        // Use searchWord for direct lookup
        await store.searchWord(state.query);
    }
};

const handleShiftEnter = async () => {
    // Force refresh mode for this query
    const previousForceRefresh = state.forceRefreshMode;
    state.forceRefreshMode = true;
    
    // Execute the query
    await handleEnter();
    
    // Restore the previous force refresh state
    state.forceRefreshMode = previousForceRefresh;
};

const handleEscape = () => {
    if (state.showControls) {
        // First priority: hide controls
        state.showControls = false;
    } else if (state.showResults) {
        // Second priority: hide results
        state.showResults = false;
    } else {
        // Finally: blur input
        state.isFocused = false;
    }
};

const toggleControls = () => {
    state.showControls = !state.showControls;
    // Don't hide results when toggling controls
};

const handleSpaceKey = (event: KeyboardEvent) => {
    handleAutocompleteSpaceKey(event);
};

const handleArrowKey = (event: KeyboardEvent) => {
    handleAutocompleteArrowKey(event);
};

const navigateResults = (direction: number) => {
    if (state.searchResults.length === 0) return;

    state.selectedIndex = Math.max(
        0,
        Math.min(
            state.searchResults.length - 1,
            state.selectedIndex + direction
        )
    );

    store.searchSelectedIndex = state.selectedIndex;
    
    // Scroll the selected item into view with improved logic
    nextTick(() => {
        const container = searchResultsComponent.value?.container;
        const selectedElement = searchResultsComponent.value?.resultRefs?.[state.selectedIndex];
        
        if (!container || !selectedElement) return;
        
        const containerRect = container.getBoundingClientRect();
        const elementRect = selectedElement.getBoundingClientRect();
        
        // Calculate if element is outside visible area
        const isAbove = elementRect.top < containerRect.top;
        const isBelow = elementRect.bottom > containerRect.bottom;
        
        if (isAbove || isBelow) {
            // Use different block positioning based on direction
            const block = direction > 0 ? 'end' : 'start';
            selectedElement.scrollIntoView({
                behavior: 'smooth',
                block: block
            });
        }
    });
};

const selectResult = async (result: SearchResult) => {
    clearTimeout(searchTimer);
    
    // Navigate to appropriate route based on mode
    const routeName = state.mode === 'thesaurus' ? 'Thesaurus' : 'Definition';
    router.push({ name: routeName, params: { word: result.word } });
    
    // Use searchWord for direct lookup (sets isDirectLookup flag)
    await store.searchWord(result.word);
};

const selectWord = async (word: string) => {
    // Use store's searchWord for direct lookup (sets isDirectLookup flag)
    await store.searchWord(word);
};

const handleForceRegenerate = () => {
    handleSearchAreaInteraction();
    state.forceRefreshMode = !state.forceRefreshMode;
};

const clearQuery = () => {
    state.query = '';
    state.searchResults = [];
    state.showResults = false;
    state.isAIQuery = false;
    state.showSparkle = false;
    searchInputComponent.value?.focus();
};

const clearAllStorage = () => {
    if (
        confirm(
            'This will clear all local storage including history and settings. Are you sure?'
        )
    ) {
        localStorage.clear();
        sessionStorage.clear();
        window.location.reload();
    }
};

// Expand modal
const handleExpandClick = () => {
    state.showExpandModal = true;
};

const closeExpandModal = () => {
    state.showExpandModal = false;
};

const submitExpandedQuery = (query: string) => {
    state.query = query;
    state.showExpandModal = false;
    nextTick(() => {
        handleEnter();
    });
};

// Update scroll state
watch(
    () => props,
    () => {
        updateScrollState();
    },
    { deep: true }
);

// Click outside handler
const handleClickOutside = (event: MouseEvent) => {
    if (!searchContainer.value || !state.showControls) return;
    
    const target = event.target as HTMLElement;
    // Check if click is outside the search container
    if (!searchContainer.value.contains(target)) {
        state.showControls = false;
    }
};

// Setup keyboard shortcuts with MagicKeys
const keys = useMagicKeys();
const shiftEnter = keys['Shift+Enter'];
const cmdEnter = keys['Cmd+Enter'];
const ctrlEnter = keys['Ctrl+Enter']; // For Windows/Linux

// Watch for force refresh shortcuts
whenever(shiftEnter, () => {
    if (state.isFocused && searchInputRef.value) {
        handleShiftEnter();
    }
});

whenever(cmdEnter, () => {
    if (state.isFocused && searchInputRef.value) {
        handleShiftEnter();
    }
});

whenever(ctrlEnter, () => {
    if (state.isFocused && searchInputRef.value) {
        handleShiftEnter();
    }
});

// Initialize
onMounted(async () => {
    // Add click outside listener
    document.addEventListener('click', handleClickOutside);
    
    // Watch query changes
    watch(
        () => state.query,
        () => {
            performSearch();
        }
    );
    
    // Watch store searchQuery changes to sync with local state
    watch(
        () => store.searchQuery,
        (newQuery) => {
            if (newQuery !== state.query) {
                state.query = newQuery;
            }
        }
    );

    // Watch for AI mode changes from store
    watch(
        () => store.sessionState?.isAIQuery,
        (isAI) => {
            if (isAI !== state.isAIQuery) {
                state.isAIQuery = isAI;
                state.showSparkle = isAI;
            }
        }
    );
    
    // Also watch the store's isAIQuery ref directly for immediate updates
    watch(
        () => store.isAIQuery,
        (isAI) => {
            if (isAI !== state.isAIQuery) {
                state.isAIQuery = isAI;
                state.showSparkle = isAI;
            }
        }
    );

    // Show results when focused with query
    watch(
        [() => state.isFocused, () => state.query, () => state.isAIQuery, () => state.searchResults],
        ([focused, query, isAI, results]) => {
            if (focused && query && query.length > 0 && !isAI && results && results.length > 0) {
                state.showResults = true;
            } else if (isAI) {
                state.showResults = false;
            }
        }
    );

    // Restore AI state if persisted
    if (store.sessionState.isAIQuery) {
        state.isAIQuery = true;
        state.showSparkle = true;
        if (store.sessionState.aiQueryText && !state.query) {
            state.query = store.sessionState.aiQueryText;
        }
    }

    // Get AI suggestions
    try {
        const history = await store.getHistoryBasedSuggestions();
        state.aiSuggestions = history.slice(0, 4);
    } catch {
        state.aiSuggestions = [];
    }
});

// Cleanup
onUnmounted(() => {
    clearTimeout(searchTimer);
    document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
/* Disable animations for reduced motion */
@media (prefers-reduced-motion: reduce) {
    * {
        animation-duration: 0.01ms !important;
        animation-iteration-count: 1 !important;
    }
}
</style>
