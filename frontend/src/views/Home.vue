<template>
    <div>
        <!-- Sidebar -->
        <Sidebar />

        <div class="min-h-screen lg:ml-sidebar-collapsed">
            <!-- Main View -->
            <div class="relative min-h-screen px-2 lg:p-4">
            <!-- Sticky Search Bar with scroll responsiveness -->
            <div :class="searchBarClasses">
                <SearchBar
                    class-name="mx-auto w-full sm:max-w-5xl"
                    :scroll-y="y"
                    :scroll-threshold="scrollThreshold"
                    :shrink-percentage="shrinkPercentage"
                    :scroll-progress="scrollProgress"
                />
            </div>

            <!-- Border separator (not sticky) -->
            <div class="border-b border-border lg:my-6"></div>

            <!-- Content Area with Sidebar -->
            <div class="container mx-auto mt-5 lg:mt-6 max-w-6xl min-h-[calc(100dvh-8rem)]">
                <div class="flex relative">
                    <!-- Progressive Sidebar (Sticky) — instant show/hide, no width transition -->
                    <div
                        v-if="shouldShowProgressiveSidebar"
                        class="hidden lg:block w-[14rem] shrink-0 overflow-visible"
                    >
                        <div class="sticky top-[5.5rem] w-[14rem] max-h-[calc(100dvh-7rem)] overflow-y-auto overflow-x-clip scrollbar-thin px-2 pt-1 pb-4">
                            <ProgressiveSidebar v-if="searchBar.searchMode === 'lookup'" />
                            <WordlistProgressiveSidebar v-else-if="searchBar.searchMode === 'wordlist'" />
                        </div>
                    </div>

                    <!-- Main Content -->
                    <div :class="['flex-1 min-w-0 max-w-5xl mx-auto', (lookupSubMode === 'suggestions' || searchBar.searchMode === 'wordlist') ? 'px-4 sm:px-2' : '']">
                        <!-- Mode switch: instant swap, no transition.
                             out-in transitions force Vue to keep the old component mounted
                             during the leave phase — unmounting 100+ wordlist cards while
                             animating causes severe jank. -->

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
import { computed, defineAsyncComponent } from 'vue';
import { useStores } from '@/stores';
import { useScroll } from '@vueuse/core';
import { SearchBar } from '@/components/custom/search';
import { DefinitionDisplay, WordSuggestionDisplay } from '@/components/custom/definition';
import EmptyState from '@/components/custom/definition/components/EmptyState.vue';
import { Sidebar } from '@/components/custom';
import { LoadingModal } from '@/components/custom/loading';
import { useRouteOrchestration } from './composables/useRouteOrchestration';

const WordListView = defineAsyncComponent(
    () => import('@/components/custom/wordlist/views/WordListView.vue'),
);
const ProgressiveSidebar = defineAsyncComponent(
    () => import('@/components/custom/navigation/ProgressiveSidebar.vue'),
);
const WordlistProgressiveSidebar = defineAsyncComponent(
    () => import('@/components/custom/navigation/WordlistProgressiveSidebar.vue'),
);

const { searchBar, content, loading } = useStores();

// Route orchestration (watchers, API calls, navigation)
useRouteOrchestration();

// Loading modal bindings
const showLoadingModal = computed({
    get: () => loading.showLoadingModal.value && searchBar.searchMode === 'lookup',
    set: (value: boolean) => loading.setShowLoadingModal(value),
});

const showSuggestionsModal = computed({
    get: () => loading.isSuggestingWords.value,
    set: (value: boolean) => {
        if (!value) loading.stopSuggestions();
    },
});

const lookupSubMode = computed(() => searchBar.getSubMode('lookup'));
const currentEntry = computed(() => content.currentEntry);

// Scroll handling
const { y } = useScroll(typeof window !== 'undefined' ? window : null);

const scrollThreshold = computed(() => {
    return (currentEntry.value || content.wordSuggestions) ? 50 : 100;
});

const scrollProgress = computed(() => {
    const maxScroll = scrollThreshold.value * 2;
    const progress = Math.min(y.value / maxScroll, 1);
    return 1 - Math.pow(1 - progress, 3);
});

const shrinkPercentage = computed(() => {
    const baseline = searchBar.isFocused ? 0 : 0.35;
    return Math.max(baseline, Math.min(scrollProgress.value * 0.85, 0.85));
});

const searchBarClasses = computed(() => [
    'relative top-0 z-dock bg-transparent sticky py-1 sm:py-1.5',
]);

const shouldShowProgressiveSidebar = computed(() => {
    if (searchBar.searchMode === 'wordlist') return true;
    if (searchBar.searchMode !== 'lookup') return false;

    if (lookupSubMode.value === 'suggestions') return !!content.wordSuggestions;

    return !!currentEntry.value?.definitions?.length;
});
</script>

<style scoped>

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
