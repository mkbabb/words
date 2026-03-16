<template>
    <div>
        <!-- Sidebar -->
        <Sidebar />

        <div
            :class="
                cn('min-h-screen transition-all duration-300 ease-in-out', {
                    'lg:ml-80': !ui.sidebarCollapsed,
                    'lg:ml-16': ui.sidebarCollapsed,
                })
            "
        >
        <!-- Main View -->
        <div class="relative min-h-screen px-2 lg:p-4">
            <!-- Sticky Search Bar with scroll responsiveness -->
            <div :class="searchBarClasses">
                <SearchBar
                    class-name="mx-auto w-full sm:max-w-4xl"
                    :scroll-y="y"
                    :scroll-threshold="scrollThreshold"
                    :shrink-percentage="shrinkPercentage"
                    :scroll-progress="scrollProgress"
                />
            </div>

            <!-- Border separator (not sticky) -->
            <div class="border-b border-border/50 lg:my-6"></div>

            <!-- Content Area with Sidebar -->
            <div class="container mx-auto max-w-6xl">
                <div class="flex gap-6 relative">
                    <!-- Progressive Sidebar (Sticky) -->
                    <div
                        class="hidden lg:block transition-all duration-200 ease-out"
                        :class="shouldShowProgressiveSidebar ? 'w-48 opacity-100' : 'w-0 opacity-0 pointer-events-none'"
                    >
                        <div
                            v-if="shouldShowProgressiveSidebar"
                            class="sticky w-48"
                            :style="{ top: '5.5rem' /* search bar height + padding */ }"
                        >
                            <ProgressiveSidebar v-if="searchBar.searchMode === 'lookup'" />
                            <WordlistProgressiveSidebar v-else-if="searchBar.searchMode === 'wordlist'" />
                        </div>
                    </div>

                    <!-- Main Content -->
                    <div :class="['flex-1 max-w-5xl mx-auto', (lookupSubMode === 'suggestions' || searchBar.searchMode === 'wordlist') ? 'px-4 sm:px-2' : '']">
                        <!-- Mode-level transition: lookup ↔ wordlist ↔ suggestions -->
                        <Transition
                    name="content-switch"
                    mode="out-in"
                    :duration="{ enter: 300, leave: 250 }"
                >
                    <!-- Definition Content (stays mounted across word changes) -->
                    <div v-if="searchBar.searchMode === 'lookup' && lookupSubMode !== 'suggestions'" key="lookup">
                        <!-- Definition Display — mount when we have data OR are actively fetching -->
                        <div v-if="content.isStreamingData || content.partialEntry || currentEntry || content.definitionError || loading.isSearching.value" class="space-y-8">
                            <DefinitionDisplay />
                        </div>

                        <!-- Empty State / Help Screen (no entry, not loading) -->
                        <div v-else class="py-8">
                            <EmptyState
                                title="Look up anything you're curious about"
                                message="Type a word above to see definitions, synonyms, and examples. You can also switch modes to explore wordlists or staging."
                                empty-type="generic"
                            />
                        </div>
                    </div>

                    <!-- Word Suggestions Content -->
                    <div v-else-if="lookupSubMode === 'suggestions'" key="suggestions">
                        <div class="space-y-8">
                            <WordSuggestionDisplay />
                        </div>
                    </div>

                    <!-- Wordlist Content -->
                    <div v-else-if="searchBar.searchMode === 'wordlist'" key="wordlist">
                        <WordListView />
                    </div>

                    <!-- Word of the Day Content -->
                    <div v-else-if="searchBar.searchMode === 'word-of-the-day'" key="word-of-the-day">
                        <div class="space-y-8">
                            <div class="py-16 text-center text-muted-foreground">
                                Word of the Day mode coming soon...
                            </div>
                        </div>
                    </div>

                    <!-- Stage Content -->
                    <div v-else-if="searchBar.searchMode === 'stage'" key="stage">
                        <div class="space-y-8">
                            <div class="py-16 text-center text-muted-foreground">
                                Stage mode coming soon...
                            </div>
                        </div>
                    </div>
                        </Transition>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Loading Modal for Lookup -->
    <LoadingModal
        v-model="showLoadingModal"
        :word="searchBar.searchQuery || 'searching'"
        :progress="loading.loadingProgress.value"
        :current-stage="loading.loadingStage.value"
        :allow-dismiss="true"
        mode="lookup"
        :dynamic-checkpoints="undefined"
        :category="loading.loadingCategory.value"
    />

    <!-- Loading Modal for AI Suggestions -->
    <LoadingModal
        v-model="showSuggestionsModal"
        :display-text="'efflorescing'"
        :progress="loading.suggestionsProgress.value"
        :current-stage="loading.suggestionsStage.value"
        mode="suggestions"
        :dynamic-checkpoints="undefined"
        :category="loading.suggestionsCategory.value"
    />
    </div>
</template>

<script setup lang="ts">
import { computed, defineAsyncComponent, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { useScroll } from '@vueuse/core';
import { cn } from '@/utils';
import { SearchBar } from '@/components/custom/search';
import { DefinitionDisplay, WordSuggestionDisplay } from '@/components/custom/definition';
import EmptyState from '@/components/custom/definition/components/EmptyState.vue';
import { Sidebar } from '@/components/custom';
import { LoadingModal } from '@/components/custom/loading';
import { useWordlistMode } from '@/stores/search/modes/wordlist';

// Lazy-loaded: only parsed when the user switches to the relevant mode
const WordListView = defineAsyncComponent(
    () => import('@/components/custom/wordlist/WordListView.vue'),
);
const ProgressiveSidebar = defineAsyncComponent(
    () => import('@/components/custom/navigation/ProgressiveSidebar.vue'),
);
const WordlistProgressiveSidebar = defineAsyncComponent(
    () => import('@/components/custom/navigation/WordlistProgressiveSidebar.vue'),
);

const { searchBar, content, ui, loading } = useStores();
const wordlistMode = useWordlistMode();
const route = useRoute();
const router = useRouter();

const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBar.searchQuery)
});

// Loading modal bindings driven by global loading store
// Show for ALL lookups (removed isDirectLookup gate that suppressed it)
const showLoadingModal = computed({
    get: () => loading.showLoadingModal.value && searchBar.searchMode === 'lookup',
    set: (value: boolean) => loading.setShowLoadingModal(value)
});

const showSuggestionsModal = computed({
    get: () => loading.isSuggestingWords.value,
    set: (value: boolean) => {
        if (!value) {
            loading.stopSuggestions();
        }
    }
});

// Computed for current lookup submode
const lookupSubMode = computed(() => searchBar.getSubMode('lookup'));

// Route orchestration — watch fullPath to catch same-route param changes (e.g. /search/hello → /search/world)
watch(() => route.fullPath, async () => {
    const routeName = route.name;
    if (routeName === 'Definition' && route.params.word) {
        const word = route.params.word as string;
        searchBar.setMode('lookup');
        searchBar.setSubMode('lookup', 'dictionary');
        searchBar.setQuery(word);

        // Close controls and results dropdowns on definition route entry
        searchBar.hideControls();
        searchBar.hideDropdown();

        // Always fetch when the word changes — skip only if we already have this exact word.
        // This is the single source of truth for definition fetches on route changes.
        if (!content.currentEntry || content.currentEntry.word !== word) {
            // Clear the old entry so child components (ProviderViewTabs) reset.
            // The card stays mounted because isStreamingData becomes true when
            // the SSE starts, before currentEntry is set.
            content.clearCurrentEntry();
            try {
                const definition = await orchestrator.getDefinition(word, {
                    onProgress: (stage, progress) => {
                        loading.setLoadingStage(stage);
                        loading.setLoadingProgress(progress);
                    }
                });
                if (definition) {
                    content.setCurrentEntry(definition);
                    // Close dropdowns after lookup completes
                    searchBar.hideControls();
                    searchBar.hideDropdown();
                }
            } catch (error: any) {
                const message = error?.message || '';
                // Silently ignore aborts (e.g. user navigated away before completion)
                if (message.includes('aborted') || error?.name === 'AbortError') {
                    return;
                }
                content.setError({
                    hasError: true,
                    errorType: 'unknown',
                    errorMessage: message || 'Failed to look up word',
                    canRetry: true,
                    originalWord: word,
                });
            }
        }
    } else if (routeName === 'Thesaurus' && route.params.word) {
        const word = route.params.word as string;
        searchBar.setMode('lookup');
        searchBar.setSubMode('lookup', 'thesaurus');
        searchBar.setQuery(word);

        // Close controls and results dropdowns on thesaurus route entry
        searchBar.hideControls();
        searchBar.hideDropdown();

        // Ensure we have the definition entry first (thesaurus needs it for the card shell)
        if (!content.currentEntry || content.currentEntry.word !== word) {
            try {
                const definition = await orchestrator.getDefinition(word, {
                    onProgress: (stage, progress) => {
                        loading.setLoadingStage(stage);
                        loading.setLoadingProgress(progress);
                    }
                });
                if (definition) {
                    content.setCurrentEntry(definition);
                }
            } catch (error: any) {
                const message = error?.message || '';
                if (message.includes('aborted') || error?.name === 'AbortError') {
                    return;
                }
                // If definition fetch fails, fall back to dictionary mode
                searchBar.setSubMode('lookup', 'dictionary');
                router.replace({ name: 'Definition', params: { word } });
                return;
            }
        }

        // Now fetch thesaurus data
        const hasThesaurus = content.currentThesaurus &&
            content.currentThesaurus.word === word;
        if (!hasThesaurus) {
            try {
                const data = await orchestrator.getThesaurusData(word);
                if (data) {
                    content.setCurrentThesaurus(data);
                    searchBar.hideControls();
                    searchBar.hideDropdown();
                }
            } catch (error: any) {
                const message = error?.message || '';
                if (message.includes('aborted') || error?.name === 'AbortError') {
                    return;
                }
                content.setError({
                    hasError: true,
                    errorType: 'unknown',
                    errorMessage: message || 'Failed to load thesaurus data',
                    canRetry: true,
                    originalWord: word,
                });
            }
        }
    } else if (routeName === 'Search' && route.params.query) {
        const query = route.params.query as string;
        searchBar.setMode('lookup');
        searchBar.setQuery(query);
        await orchestrator.performSearch();
    } else if (routeName === 'Wordlist' && route.params.wordlistId) {
        const wordlistId = route.params.wordlistId as string;
        searchBar.clearQuery();
        content.clearCurrentEntry();
        searchBar.setMode('wordlist');
        const { wordlistMode } = useStores();
        wordlistMode.setWordlist(wordlistId);
    } else if (routeName === 'WordlistSearch' && route.params.wordlistId) {
        const wordlistId = route.params.wordlistId as string;
        const query = (route.params.query as string) || '';
        content.clearCurrentEntry();
        searchBar.setMode('wordlist');
        const { wordlistMode } = useStores();
        wordlistMode.setWordlist(wordlistId);
        if (query) {
            searchBar.setQuery(query);
        } else {
            searchBar.clearQuery();
        }
    } else if (routeName === 'Home') {
        searchBar.clearQuery();
        content.clearCurrentEntry();
    }
}, { immediate: true });

// Watch search mode changes for clearing content
watch(() => searchBar.searchMode, (newMode, oldMode) => {
    if (newMode !== oldMode && newMode !== 'lookup') {
        content.clearCurrentEntry();
    }
});

// State from stores
const currentEntry = computed(() => content.currentEntry);

// Scroll handling with responsive thresholds
const { y } = useScroll(typeof window !== 'undefined' ? window : null);

const scrollThreshold = computed(() => {
    const hasContent = currentEntry.value || content.wordSuggestions;
    return hasContent ? 50 : 100;
});

const scrollProgress = computed(() => {
    const threshold = scrollThreshold.value;
    const scrollPos = y.value;
    const maxScroll = threshold * 2;
    const progress = Math.min(scrollPos / maxScroll, 1);
    return 1 - Math.pow(1 - progress, 3);
});

const shrinkPercentage = computed(() => {
    const progress = scrollProgress.value;
    const baseline = searchBar.isFocused ? 0 : 0.35;
    return Math.max(baseline, Math.min(progress * 0.85, 0.85));
});

const searchBarClasses = computed(() => [
    'relative top-0 z-40 bg-transparent',
    'sticky',
    'py-1 sm:py-1.5',
]);

const shouldShowProgressiveSidebar = computed(() => {
    // Hide when left sidebar is expanded — give main content more room
    if (!ui.sidebarCollapsed) return false;

    if (searchBar.searchMode === 'wordlist') {
        return !!wordlistMode.selectedWordlist;
    }

    const hasDefinition = !!currentEntry.value;
    const isLookupMode = searchBar.searchMode === 'lookup';
    const isSuggestionsSubMode = lookupSubMode.value === 'suggestions';
    const hasSuggestions = !!content.wordSuggestions;

    return isLookupMode && (hasDefinition || (isSuggestionsSubMode && hasSuggestions));
});

onMounted(async () => {
    if (searchBar.searchMode === 'wordlist') {
        // Wordlist initialization handled by mode store
    }
});
</script>

<style scoped>
/* Content switch animation */
.content-switch-enter-active,
.content-switch-leave-active {
    transition: opacity 0.3s var(--ease-apple-default),
                transform 0.3s var(--ease-apple-default);
}

.content-switch-enter-from {
    opacity: 0;
    transform: translateY(10px);
}

.content-switch-enter-to {
    opacity: 1;
    transform: translateY(0);
}

.content-switch-leave-from {
    opacity: 1;
    transform: translateY(0);
}

.content-switch-leave-to {
    opacity: 0;
    transform: translateY(-10px);
}

@keyframes cardFadeIn {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-card-fade-in {
    animation: cardFadeIn 0.4s var(--ease-apple-default) forwards;
}
</style>
