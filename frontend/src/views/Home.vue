<template>
    <!-- Sidebar -->
    <Sidebar />

    <div
        :class="
            cn('min-h-screen transition-all duration-300 ease-in-out', {
                'lg:ml-80': !store.sidebarCollapsed,
                'lg:ml-16': store.sidebarCollapsed,
            })
        "
    >
        <!-- Main View -->
        <div class="relative min-h-screen p-2 lg:p-4">
            <!-- Sticky Search Bar with scroll responsiveness -->
            <div :class="searchBarClasses">
                <SearchBar
                    :shrink-percentage="shrinkPercentage"
                    @stage-enter="handleStageEnter"
                />
            </div>

            <!-- Border separator (not sticky) -->
            <div class="border-b border-border/50"></div>

            <!-- Content Area -->
            <div class="container mx-auto max-w-5xl px-2 py-4 sm:px-2 sm:py-8">
                <!-- Animated Content Cards -->
                <Transition
                    mode="out-in"
                    enter-active-class="transition-all duration-300 ease-apple-bounce"
                    leave-active-class="transition-all duration-200 ease-out"
                    enter-from-class="opacity-0 scale-95 translate-x-8 rotate-1"
                    enter-to-class="opacity-100 scale-100 translate-x-0 rotate-0"
                    leave-from-class="opacity-100 scale-100 translate-x-0 rotate-0"
                    leave-to-class="opacity-0 scale-95 -translate-x-8 -rotate-1"
                >
                    <!-- Definition Content -->
                    <div v-if="store.searchMode === 'lookup'" key="lookup">
                        <!-- Loading State -->
                        <div v-if="isSearching" class="space-y-8">
                            <DefinitionSkeleton />
                        </div>

                        <!-- Definition Display -->
                        <div v-else-if="currentEntry" class="space-y-8">
                            <DefinitionDisplay />
                        </div>

                        <!-- Empty State -->
                        <div v-else class="py-16 text-center">
                            <!-- Empty state - no text -->
                        </div>
                    </div>

                    <!-- Wordlist Content -->
                    <div
                        v-else-if="store.searchMode === 'wordlist'"
                        key="wordlist"
                    >
                        <div class="space-y-8">
                            <!-- Wordlist content will go here -->
                            <div
                                class="py-16 text-center text-muted-foreground"
                            >
                                Wordlist mode coming soon...
                            </div>
                        </div>
                    </div>

                    <!-- Stage Content -->
                    <div v-else-if="store.searchMode === 'stage'" key="stage">
                        <div class="space-y-8">
                            <StageTest ref="stageTestRef" />
                        </div>
                    </div>
                </Transition>
            </div>
        </div>
    </div>

    <!-- Loading Modal -->
    <LoadingModal
        v-model="isSearching"
        :word="store.searchQuery || 'searching'"
        :progress="store.loadingProgress"
        :current-stage="store.loadingStage"
        :facts="currentFacts"
    />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useAppStore } from '@/stores';
import { useScroll } from '@vueuse/core';
import { cn } from '@/utils';
import { SearchBar } from '@/components/custom/search';
import { DefinitionDisplay } from '@/components/custom/definition';
import { DefinitionSkeleton } from '@/components/custom/definition';
import { Sidebar } from '@/components/custom';
import { LoadingModal } from '@/components/custom/loading';
import { StageTest } from '@/components/custom/test';
import { dictionaryApi } from '@/utils/api';
import type { FactItem } from '@/types';

const store = useAppStore();

// Component refs
const stageTestRef = ref();

// Facts for loading modal
const currentFacts = ref<FactItem[]>([]);

// Handle stage mode enter key
const handleStageEnter = (_query: string) => {
    if (stageTestRef.value && stageTestRef.value.startMockTest) {
        stageTestRef.value.startMockTest();
    }
};

// Watch for search queries to fetch facts
watch(
    () => store.searchQuery,
    async (newQuery) => {
        if (newQuery && store.isSearching) {
            try {
                // Fetch facts asynchronously while search is happening
                const factsResponse = await dictionaryApi.getWordFacts(
                    newQuery,
                    5,
                    store.lookupHistory.slice(-10).map((h) => h.word)
                );
                currentFacts.value = factsResponse.facts;
            } catch (error) {
                console.warn('Failed to fetch facts:', error);
                currentFacts.value = [];
            }
        } else if (!newQuery) {
            currentFacts.value = [];
        }
    },
    { immediate: true }
);

onMounted(async () => {
    console.log('Home component mounted');
    console.log('Has searched:', store.hasSearched);
    console.log('Search results:', store.searchResults);

    // Ensure vocabulary suggestions are loaded
    if (store.vocabularySuggestions.length === 0) {
        await store.refreshVocabularySuggestions();
    }
});

const isSearching = computed(() => store.isSearching);
const currentEntry = computed(() => store.currentEntry);

// Scroll-based shrinking animation
const { y } = useScroll(window);
const scrollThreshold = 100;

const isScrolled = computed(() => y.value > scrollThreshold);
const shrinkPercentage = computed(() => {
    if (y.value <= scrollThreshold) return 0;
    return Math.min((y.value - scrollThreshold) / 60, 1);
});

const searchBarClasses = computed(() => {
    return cn(
        'sticky top-0 z-40 transition-all duration-300 ease-out',
        isScrolled.value ? 'py-2' : 'py-4'
    );
});
</script>
