<template>
    <div class="space-y-6">
        <!-- Header (only when a wordlist is selected) -->
        <div v-if="currentWordlist" class="flex items-center justify-between">
            <div>
                <h1 class="text-2xl font-bold">
                    {{ currentWordlist.name }}
                </h1>
                <p
                    v-if="currentWordlist.description"
                    class="mt-1 text-sm text-muted-foreground"
                >
                    {{ currentWordlist.description }}
                </p>
            </div>
        </div>

        <!-- Statistics + Review Button -->
        <WordlistStatsBar
            v-if="currentWordlist"
            :wordlist="currentWordlist"
            :mastered="masteryStats.gold"
            :due-for-review="dueForReview"
        >
            <template #actions>
                <Button
                    v-if="dueForReview > 0"
                    size="sm"
                    @click="showReviewModal = true"
                >
                    Start Review ({{ dueForReview }})
                </Button>
            </template>
        </WordlistStatsBar>

        <!-- Loading State -->
        <div
            v-if="isLoading"
            class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
        >
            <div v-for="i in 8" :key="i" class="animate-pulse">
                <div class="h-24 rounded-lg bg-muted"></div>
            </div>
        </div>

        <!-- Empty State / Help Screen -->
        <div
            v-else-if="!currentWordlist || currentWords.length === 0"
            class="py-8"
        >
            <!-- No wordlist selected (or none available) -->
            <EmptyState
                v-if="!currentWordlist"
                title="Start with a wordlist"
                message="Create a new wordlist or select one from the sidebar to begin reviewing words."
                empty-type="generic"
            />

            <!-- Selected wordlist but no words / no matches -->
            <EmptyState
                v-else
                title="This wordlist is feeling empty"
                :message="
                    searchBar.searchQuery
                        ? 'No words match this search. Try changing your query or filters.'
                        : 'Add words to this list or upload a file to get started.'
                "
                empty-type="generic"
            />
        </div>

        <!-- Word Cards Grid -->
        <div v-else class="space-y-4">
            <TransitionGroup
                ref="scrollContainer"
                tag="div"
                name="card-grid"
                class="grid grid-cols-2 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
            >
                <WordListCard
                    v-for="word in currentWords"
                    :key="word._uniqueId"
                    :word="word"
                    @click="handleWordClick"
                    @review="() => showReviewModal = true"
                    @edit="handleEdit"
                    @visited="handleVisited"
                    @remove="handleRemove"
                />
            </TransitionGroup>

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

        <!-- Review Modal -->
        <ReviewModal
            v-if="currentWordlist"
            v-model="showReviewModal"
            :wordlist-id="currentWordlist.id"
            :wordlist-name="currentWordlist.name"
            @session-complete="handleReviewSessionComplete"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { Button } from '@/components/ui/button';
import type { WordListItem, WordList } from '@/types';
import { wordlistApi } from '@/api';
import { useToast } from '@/components/ui/toast/use-toast';
import WordListCard from './WordListCard.vue';
import WordlistStatsBar from './WordlistStatsBar.vue';
import WordListUploadModal from './modals/WordListUploadModal.vue';
import CreateWordListModal from './modals/CreateWordListModal.vue';
import EditWordNotesModal from './modals/EditWordNotesModal.vue';
import ReviewModal from './modals/ReviewModal.vue';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { applySortCriteria } from './utils/sortWords';
import { logger } from '@/utils/logger';
import EmptyState from '@/components/custom/definition/components/EmptyState.vue';

const { searchBar } = useStores();
const wordlistMode = useWordlistMode();
const searchBarStore = useSearchBarStore();
const router = useRouter();

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
const showReviewModal = ref(false);
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
            (word: any) => word.review_data?.next_review_date && new Date(word.review_data.next_review_date) <= now
        );
    }

    // Apply sort criteria
    if (sortCriteria.value.length > 0) {
        items = applySortCriteria(items, sortCriteria.value);
    }

    // Add unique keys for Vue (stable keys, no Date.now())
    return items.map((item: any, index: number) => ({
        ...item,
        _uniqueId: `${item.word}-${index}`,
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
        (word) => word.review_data?.next_review_date && new Date(word.review_data.next_review_date) <= now
    ).length;
});

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

const handleWordClick = (word: WordListItem) => {
    // Switch to lookup mode and navigate — route watcher handles the fetch
    searchBarStore.setMode('lookup');
    router.push({ name: 'Definition', params: { word: word.word } });
};

const handleVisited = async (word: WordListItem) => {
    if (!currentWordlist.value?.id) return;
    try {
        await wordlistApi.markWordVisited(currentWordlist.value.id, word.word);
    } catch (error) {
        logger.error('Failed to mark visited:', error);
    }
};

const handleRemove = async (word: WordListItem) => {
    if (!currentWordlist.value?.id) return;
    try {
        await wordlistApi.removeWord(currentWordlist.value.id, word.word);
        // Optimistic update
        const updated = [...wordlistMode.results].filter(
            (w: any) => w.word !== word.word
        );
        wordlistMode.setResults(updated as any);
        toast({ title: 'Word removed', description: `"${word.word}" removed from list.` });
    } catch (error) {
        logger.error('Failed to remove word:', error);
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

const handleWordsUploaded = async (_words: string[]) => {
    // Re-fetch wordlist data after upload
    if (wordlistMode.selectedWordlist) {
        await loadWordlistMeta(wordlistMode.selectedWordlist);
        await triggerWordlistSearch();
        toast({
            title: 'Words uploaded',
            description: 'Your wordlist has been updated.',
        });
    }
};

const handleReviewSessionComplete = async () => {
    // Refresh wordlist data after review session
    if (wordlistMode.selectedWordlist) {
        await loadWordlistMeta(wordlistMode.selectedWordlist);
        await triggerWordlistSearch();
    }
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
            id: (response.data as any)._id || response.data.id,
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
/* Card grid transitions */
.card-grid-enter-active {
    transition: opacity 0.3s ease, transform 0.3s ease;
}
.card-grid-leave-active {
    transition: opacity 0.2s ease, transform 0.2s ease;
}
.card-grid-enter-from {
    opacity: 0;
    transform: translateY(8px) scale(0.97);
}
.card-grid-leave-to {
    opacity: 0;
    transform: scale(0.97);
}
.card-grid-move {
    transition: transform 0.3s ease;
}
</style>
