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
        <div class="relative min-h-screen p-0 lg:p-4">
            <!-- Sticky Search Bar with scroll responsiveness -->
            <div :class="searchBarClasses">
                <div class="mx-auto w-full sm:max-w-4xl">
                    <SearchBar
                        :scroll-y="y"
                        :scroll-threshold="scrollThreshold"
                        :shrink-percentage="shrinkPercentage"
                        :scroll-progress="scrollProgress"
                    />
                </div>
            </div>

            <!-- Border separator (not sticky) -->
            <div class="border-b border-border/50 lg:my-6"></div>

            <!-- Content Area with Sidebar -->
            <div class="container mx-auto max-w-6xl">
                <div class="flex gap-6 relative">
                    <!-- Progressive Sidebar (Sticky) -->
                    <div
                        class="hidden xl:block transition-all duration-300 ease-out"
                        :class="shouldShowProgressiveSidebar ? 'w-48 opacity-100' : 'w-0 opacity-0'"
                    >
                        <div
                            v-if="shouldShowProgressiveSidebar"
                            class="sticky w-48"
                            :style="{ top: '5.5rem', zIndex: 30 }"
                        >
                            <ProgressiveSidebar />
                        </div>
                    </div>

                    <!-- Main Content -->
                    <div :class="['flex-1 max-w-5xl mx-auto', (lookupSubMode === 'suggestions' || searchBar.searchMode === 'wordlist') ? 'px-4 sm:px-2' : '']">
                        <!-- Animated Content Cards -->
                        <Transition
                    name="content-switch"
                    mode="out-in"
                    :duration="{ enter: 300, leave: 500 }"
                >
                    <!-- Definition Content -->
                    <div v-if="searchBar.searchMode === 'lookup' && lookupSubMode !== 'suggestions'" key="lookup">
                        <!-- Loading State -->
                        <div v-if="loading.isSearching.value && loading.showLoadingModal.value && !content.partialEntry" class="space-y-8">
                            <DefinitionSkeleton />
                        </div>

                        <!-- Definition Display -->
                        <div v-else-if="content.isStreamingData || content.partialEntry || currentEntry || content.definitionError" class="space-y-8">
                            <DefinitionDisplay />
                        </div>

                        <!-- Empty State -->
                        <div v-else class="py-16 text-center">
                            <!-- Empty state - no text -->
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
import { computed, onMounted, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useStores } from '@/stores';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { useScroll } from '@vueuse/core';
import { cn } from '@/utils';
import { SearchBar } from '@/components/custom/search';
import { DefinitionDisplay, WordSuggestionDisplay } from '@/components/custom/definition';
import { DefinitionSkeleton } from '@/components/custom/definition';
import { Sidebar } from '@/components/custom';
import { LoadingModal } from '@/components/custom/loading';
import WordListView from '@/components/custom/wordlist/WordListView.vue';
import { ProgressiveSidebar } from '@/components/custom/navigation';

const { searchBar, content, ui, loading } = useStores();
const route = useRoute();

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

        if (!content.currentEntry || content.currentEntry.word !== word) {
            searchBar.setDirectLookup(true);
            try {
                await orchestrator.getDefinition(word, {
                    onProgress: (stage, progress) => {
                        loading.setLoadingStage(stage);
                        loading.setLoadingProgress(progress);
                    }
                });
            } finally {
                searchBar.setDirectLookup(false);
            }
        }
    } else if (routeName === 'Thesaurus' && route.params.word) {
        const word = route.params.word as string;
        searchBar.setMode('lookup');
        searchBar.setSubMode('lookup', 'thesaurus');
        searchBar.setQuery(word);

        if (!content.currentEntry || content.currentEntry.word !== word) {
            searchBar.setDirectLookup(true);
            try {
                await orchestrator.getThesaurusData(word);
            } finally {
                searchBar.setDirectLookup(false);
            }
        }
    } else if (routeName === 'Search' && route.params.query) {
        const query = route.params.query as string;
        searchBar.setMode('lookup');
        searchBar.setQuery(query);
        await orchestrator.performSearch();
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
    'transition-all duration-300 ease-out',
    'sticky',
    {
        'py-8': scrollProgress.value < 0.3,
        'py-4': scrollProgress.value >= 0.3 && scrollProgress.value < 0.7,
        'py-2': scrollProgress.value >= 0.7,
    },
]);

const shouldShowProgressiveSidebar = computed(() => {
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
    transition: all 0.3s cubic-bezier(0.25, 0.46, 0.45, 0.94);
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
    animation: cardFadeIn 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}
</style>
