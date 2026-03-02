<template>
    <div class="space-y-6">
        <!-- Header -->
        <div class="flex items-center justify-between">
            <div>
                <h1 class="text-2xl font-bold">
                    {{ currentWordlist?.name || 'Wordlist' }}
                </h1>
                <p
                    v-if="currentWordlist?.description"
                    class="mt-1 text-muted-foreground"
                >
                    {{ currentWordlist.description }}
                </p>
            </div>
        </div>

        <!-- Statistics -->
        <WordlistStatsBar
            :wordlist="currentWordlist"
            :mastered="masteryStats.gold"
            :due-for-review="dueForReview"
        />

        <!-- Loading State -->
        <div
            v-if="isLoading"
            class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        >
            <div v-for="i in 8" :key="i" class="animate-pulse">
                <div class="h-24 rounded-lg bg-muted"></div>
            </div>
        </div>

        <!-- Empty State -->
        <div
            v-else-if="!currentWordlist || currentWords.length === 0"
            class="py-16 text-center"
        >
            <div class="mx-auto max-w-sm">
                <div v-if="!currentWordlist" class="space-y-4">
                    <BookOpen
                        class="mx-auto h-16 w-16 text-muted-foreground/50"
                    />
                    <h3 class="text-lg font-semibold">No Wordlist Selected</h3>
                    <p class="text-muted-foreground">
                        Select a wordlist from the sidebar to start learning.
                    </p>
                </div>
                <div v-else class="space-y-4">
                    <FileText
                        class="mx-auto h-16 w-16 text-muted-foreground/50"
                    />
                    <h3 class="text-lg font-semibold">No Words Found</h3>
                    <p class="text-muted-foreground">
                        {{
                            searchBar.searchQuery
                                ? 'Try adjusting your search or filters.'
                                : 'Add some words to get started.'
                        }}
                    </p>
                </div>
            </div>
        </div>

        <!-- Word Cards Grid -->
        <div v-else class="space-y-4">
            <div
                ref="scrollContainer"
                class="grid grid-cols-2 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
            >
                <WordListCard
                    v-for="word in currentWords"
                    :key="word._uniqueId"
                    :word="word"
                    @click="handleWordClick"
                    @review="handleReview"
                    @edit="handleEdit"
                />
            </div>

            <!-- Load More Button -->
            <div
                v-if="!isLoadingWords && hasMoreWords"
                class="flex justify-center py-6"
            >
                <Button @click="loadMoreWords" variant="outline" size="lg">
                    Load More Words ({{ remainingWordsCount }} remaining)
                </Button>
            </div>

            <!-- Loading indicator -->
            <div
                v-else-if="isLoadingWords"
                class="flex items-center justify-center py-4"
            >
                <div
                    class="h-4 w-4 animate-spin rounded-full border-b-2 border-primary"
                ></div>
                <span class="ml-2 text-sm text-muted-foreground"
                    >Loading more...</span
                >
            </div>

            <!-- End of results -->
            <div
                v-else-if="!hasMoreWords && currentWords.length > 0"
                class="py-4 text-center"
            >
                <span class="text-xs text-muted-foreground"
                    >All words loaded</span
                >
            </div>
        </div>

        <!-- File Upload Modal -->
        <WordListUploadModal
            v-model="showUploadModal"
            :wordlist-id="currentWordlist?.id"
            @uploaded="handleWordsUploaded"
            @wordlists-updated="() => {}"
        />

        <!-- Create Wordlist Modal -->
        <CreateWordListModal
            v-model="showCreateModal"
            @created="handleWordlistCreated"
        />

        <!-- Edit Word Notes Modal -->
        <EditWordNotesModal
            v-model="showEditNotesModal"
            :word="editingWord"
            @save="updateWordNotes"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useStores } from '@/stores';
import { BookOpen, FileText } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import type { WordListItem, WordList } from '@/types';
import { wordlistApi } from '@/api';
import { useToast } from '@/components/ui/toast/use-toast';
import WordListCard from './WordListCard.vue';
import WordlistStatsBar from './WordlistStatsBar.vue';
import WordListUploadModal from './modals/WordListUploadModal.vue';
import CreateWordListModal from './modals/CreateWordListModal.vue';
import EditWordNotesModal from './modals/EditWordNotesModal.vue';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { applySortCriteria } from './utils/sortWords';
import { logger } from '@/utils/logger';

const { searchBar } = useStores();
const wordlistMode = useWordlistMode();
const searchBarStore = useSearchBarStore();

// Create orchestrator for API operations
const orchestrator = useSearchOrchestrator({
    query: computed(() => searchBarStore.searchQuery),
});
const { toast } = useToast();

// Component state
const isLoadingMeta = ref(false);
const isLoadingWords = ref(false);
const showUploadModal = ref(false);
const showCreateModal = ref(false);
const showEditNotesModal = ref(false);
const editingWord = ref<WordListItem | null>(null);
const currentWordlistData = ref<WordList | null>(null);
const currentPage = ref(0);
const scrollContainer = ref<HTMLElement>();
void scrollContainer; // bound via template ref="scrollContainer"

// Filters from wordlist mode store
const filters = computed(() => wordlistMode.wordlistFilters);

// Sort criteria from wordlist mode store (writeable)
const sortCriteria = computed({
    get: () => wordlistMode.wordlistSortCriteria,
    set: (value: any[]) => {
        wordlistMode.setWordlistSortCriteria(value);
    },
});

// ---------------------------------------------------------------------------
// Single derived computed: store.filteredResults + wordlistFilters + sort
// ---------------------------------------------------------------------------

/**
 * Apply the wordlist panel's boolean filters (showBronze, showSilver, etc.)
 * on top of the store's filteredResults, then sort.
 */
const currentWords = computed(() => {
    let items: WordListItem[] = [...wordlistMode.filteredResults];

    // Apply mastery-level panel filters
    if (
        !filters.value.showBronze ||
        !filters.value.showSilver ||
        !filters.value.showGold
    ) {
        items = items.filter((word: any) => {
            if (word.mastery_level === 'bronze' && !filters.value.showBronze)
                return false;
            if (word.mastery_level === 'silver' && !filters.value.showSilver)
                return false;
            if (word.mastery_level === 'gold' && !filters.value.showGold)
                return false;
            return true;
        });
    }

    // Apply hot/due panel filters
    if (filters.value.showHotOnly) {
        items = items.filter((word: any) => word.temperature === 'hot');
    }
    if (filters.value.showDueOnly) {
        const now = new Date();
        items = items.filter(
            (word: any) => new Date(word.review_data?.next_review_date) <= now
        );
    }

    // Apply sort criteria
    if (sortCriteria.value.length > 0) {
        items = applySortCriteria(items, sortCriteria.value);
    }

    // Add unique keys for Vue
    return items.map((item: any, index: number) => ({
        ...item,
        _uniqueId: `${item.word}-${index}-${Date.now()}`,
    }));
});

// Computed properties
const currentWordlist = computed(() => currentWordlistData.value);
const isLoading = computed(() => isLoadingMeta.value || isLoadingWords.value);

const hasMoreWords = computed(() => {
    return wordlistMode.pagination.hasMore;
});

const remainingWordsCount = computed(() => {
    return Math.max(
        0,
        wordlistMode.pagination.total - wordlistMode.results.length
    );
});

const masteryStats = computed(() => {
    if (!currentWords.value || currentWords.value.length === 0) {
        return { bronze: 0, silver: 0, gold: 0 };
    }

    return currentWords.value.reduce(
        (acc: Record<string, number>, word: any) => {
            acc[word.mastery_level] = (acc[word.mastery_level] || 0) + 1;
            return acc;
        },
        { bronze: 0, silver: 0, gold: 0 }
    );
});

const dueForReview = computed(() => {
    if (!currentWords.value || currentWords.value.length === 0) return 0;

    const now = new Date();
    return currentWords.value.filter(
        (word) => new Date(word.review_data.next_review_date) <= now
    ).length;
});

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

const handleWordClick = async (word: WordListItem) => {
    // Switch to lookup mode and navigate to definition route
    searchBarStore.setMode('lookup');

    // Perform the word lookup after navigation
    searchBar.isDirectLookup = true;
    try {
        await orchestrator.getDefinition(word.word);
    } finally {
        searchBar.isDirectLookup = false;
    }
};

const handleReview = async (word: WordListItem, quality: number) => {
    try {
        if (!currentWordlist.value?.id) {
            logger.error('No wordlist selected');
            return;
        }

        // Submit review to backend
        const response = await wordlistApi.submitWordReview(
            currentWordlist.value.id,
            {
                word: word.word,
                quality,
            }
        );

        // Update the word in the store results so our computed refreshes
        if (response.data) {
            const storeResults = [...wordlistMode.results] as WordListItem[];
            const wordIndex = storeResults.findIndex(
                (w) => w.word === word.word
            );
            if (wordIndex >= 0) {
                storeResults[wordIndex] = {
                    ...storeResults[wordIndex],
                    mastery_level:
                        response.data.mastery_level ||
                        storeResults[wordIndex].mastery_level,
                    review_data: {
                        ...storeResults[wordIndex].review_data,
                        last_review_date:
                            response.data.last_reviewed ||
                            new Date().toISOString(),
                    },
                } as any;
                wordlistMode.setResults(storeResults);
            }
        }
    } catch (error) {
        logger.error('Failed to process review:', error);
    }
};

const handleEdit = (word: WordListItem) => {
    editingWord.value = word;
    showEditNotesModal.value = true;
};

const updateWordNotes = async (word: WordListItem, newNotes: string) => {
    try {
        if (!currentWordlist.value?.id) {
            logger.error('No wordlist selected');
            return;
        }

        // Update in the store results so our computed refreshes
        const storeResults = [...wordlistMode.results] as WordListItem[];
        const wordIndex = storeResults.findIndex((w) => w.word === word.word);
        if (wordIndex >= 0) {
            storeResults[wordIndex] = {
                ...storeResults[wordIndex],
                notes: newNotes,
            } as any;
            wordlistMode.setResults(storeResults);
        }
    } catch (error) {
        logger.error('Failed to update notes:', error);
        toast({
            title: 'Error',
            description: 'Failed to update notes. Please try again.',
            variant: 'destructive',
        });
    }
};

const handleWordsUploaded = (_words: string[]) => {
    // Refresh current wordlist - stub for now
};

const handleWordlistCreated = async (wordlist: any) => {
    wordlistMode.setWordlist(wordlist.id);
    searchBarStore.setMode('wordlist');
};

const loadWordlistMeta = async (id: string) => {
    if (!id) return;

    isLoadingMeta.value = true;
    try {
        const response = await wordlistApi.getWordlist(id);

        currentWordlistData.value = {
            id: response.data._id || response.data.id,
            name: response.data.name,
            description: response.data.description,
            hash_id: response.data.hash_id,
            words: [], // Words loaded separately
            total_words: response.data.total_words,
            unique_words: response.data.unique_words,
            learning_stats: response.data.learning_stats,
            last_accessed: response.data.last_accessed,
            created_at: response.data.created_at,
            updated_at: response.data.updated_at,
            metadata: response.data.metadata || {},
            tags: response.data.tags || [],
            is_public: response.data.is_public || false,
            owner_id: response.data.owner_id,
        };
    } catch (error) {
        logger.error('Failed to load wordlist metadata:', error);
    } finally {
        isLoadingMeta.value = false;
    }
};

// Simplified loading - delegates to orchestrator for API calls
const triggerWordlistSearch = async () => {
    if (wordlistMode.selectedWordlist) {
        const wordlistId = wordlistMode.selectedWordlist;
        const query = searchBar.searchQuery.trim();

        isLoadingWords.value = true;
        try {
            if (!query) {
                await orchestrator.executeWordlistFetch(wordlistId);
                searchBar.hideDropdown();
            } else {
                const results = await orchestrator.executeWordlistSearchApi(
                    wordlistId,
                    query
                );

                if (results.length > 0) {
                    searchBar.openDropdown();
                    searchBar.setSelectedIndex(0);
                } else {
                    searchBar.hideDropdown();
                }
            }
        } catch (error) {
            logger.error('Wordlist search error:', error);
            wordlistMode.clearResults();
            searchBar.hideDropdown();
        } finally {
            isLoadingWords.value = false;
        }
    }
};

const loadMoreWords = async () => {
    isLoadingWords.value = true;
    try {
        await orchestrator.loadMoreWordlist();
    } catch (error) {
        logger.error('Failed to load more words:', error);
    } finally {
        isLoadingWords.value = false;
    }
};

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

onMounted(async () => {
    // The watcher with immediate: true will handle initial load
});

onUnmounted(() => {
    // Cleanup handled automatically
});

// Watch for wordlist changes
watch(
    () => wordlistMode.selectedWordlist,
    async (newId) => {
        if (newId) {
            // Reset state when changing wordlists
            currentPage.value = 0;

            // Load metadata
            await loadWordlistMeta(newId);
            // Trigger search through orchestrator
            await triggerWordlistSearch();
        } else {
            currentWordlistData.value = null;
        }
    },
    { immediate: true }
);

// Watch for search query changes
watch(
    () => searchBar.searchQuery,
    async () => {
        if (
            searchBarStore.searchMode === 'wordlist' &&
            wordlistMode.selectedWordlist
        ) {
            await triggerWordlistSearch();
        }
    }
);
</script>

<style scoped>
/* Additional component-specific styles if needed */
</style>
