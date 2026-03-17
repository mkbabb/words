<template>
    <div ref="gridContainer" class="space-y-6">
        <!-- Wordlist content with switch transition -->
        <Transition name="wordlist-switch" mode="out-in">
            <div v-if="currentWordlist" :key="currentWordlist.id" class="space-y-6">
                <!-- Header -->
                <div class="flex items-center justify-between border-b border-border/50 pb-4">
                    <div>
                        <h1 class="text-2xl font-serif font-bold">
                            {{ currentWordlist.name }}
                        </h1>
                        <p
                            v-if="currentWordlist.description"
                            class="mt-1 text-sm font-serif text-muted-foreground"
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

                <!-- Tabs: Words / Review -->
                <Tabs
                    v-model="activeTab"
                    class="w-full"
                >
                    <TabsList class="inline-flex w-auto justify-start bg-transparent dark:bg-transparent border-none dark:border-transparent shadow-none backdrop-blur-none p-0 h-auto rounded-none gap-6 [&>div:first-child]:hidden">
                        <TabsTrigger value="words" class="font-serif text-2xl font-bold lowercase tracking-wide px-0 py-1 h-auto flex-none rounded-none border-none shadow-none bg-transparent dark:bg-transparent data-[state=active]:bg-transparent dark:data-[state=active]:bg-transparent data-[state=active]:shadow-none dark:data-[state=active]:shadow-none data-[state=active]:underline data-[state=active]:underline-offset-8 data-[state=active]:decoration-2 text-muted-foreground/50 data-[state=active]:text-foreground dark:data-[state=active]:text-foreground dark:text-muted-foreground/50">
                            words
                        </TabsTrigger>
                        <TabsTrigger value="review" class="font-serif text-2xl font-bold lowercase tracking-wide px-0 py-1 h-auto flex-none rounded-none border-none shadow-none bg-transparent dark:bg-transparent data-[state=active]:bg-transparent dark:data-[state=active]:bg-transparent data-[state=active]:shadow-none dark:data-[state=active]:shadow-none data-[state=active]:underline data-[state=active]:underline-offset-8 data-[state=active]:decoration-2 text-muted-foreground/50 data-[state=active]:text-foreground dark:data-[state=active]:text-foreground dark:text-muted-foreground/50">
                            review
                            <span
                                v-if="dueForReview > 0"
                                class="ml-1.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary/15 px-1.5 text-micro font-medium text-primary tabular-nums"
                            >
                                {{ dueForReview }}
                            </span>
                        </TabsTrigger>
                    </TabsList>

                    <!-- Words Tab -->
                    <TabsContent value="words" class="mt-4">
                        <!-- Loading State -->
                        <div
                            v-if="isInitialLoading"
                            class="grid gap-x-2 gap-y-1.5 grid-cols-[repeat(auto-fill,minmax(140px,1fr))]"
                        >
                            <div v-for="i in 8" :key="i" class="animate-pulse">
                                <div class="h-24 rounded-lg bg-muted"></div>
                            </div>
                        </div>

                        <!-- Empty State -->
                        <div
                            v-else-if="currentWords.length === 0 && !isLoadingWords"
                            class="py-8"
                        >
                            <EmptyState
                                title="This wordlist is feeling empty"
                                :message="
                                    searchBar.searchQuery
                                        ? 'No words match this search. Try changing your query or filters.'
                                        : 'Add words to this list or upload a file to get started.'
                                "
                                empty-type="generic"
                            />
                        </div>

                        <!-- Word Cards Grid (Virtualized) -->
                        <div v-else class="space-y-4">
                            <div
                                :style="{ height: `${virtualizer.getTotalSize()}px`, position: 'relative', width: '100%' }"
                            >
                                <div
                                    v-for="virtualRow in virtualizer.getVirtualItems()"
                                    :key="String(virtualRow.key)"
                                    :style="{
                                        position: 'absolute',
                                        top: 0,
                                        left: 0,
                                        width: '100%',
                                        transform: `translateY(${virtualRow.start}px)`,
                                    }"
                                    :ref="(el) => measureElement(el as HTMLElement)"
                                >
                                    <div class="grid gap-x-2 gap-y-1.5 grid-cols-[repeat(auto-fill,minmax(140px,1fr))]">
                                        <WordListCard
                                            v-for="word in rows[virtualRow.index]"
                                            :key="word.word"
                                            :word="word"
                                            @click="handleWordClick"
                                            @lookup="handleCardLookup"
                                            @review="() => showReviewModal = true"
                                            @edit="handleEdit"
                                            @visited="handleVisited"
                                            @remove="handleRemove"
                                        />
                                    </div>
                                </div>
                            </div>

                            <!-- Loading indicator for infinite scroll -->
                            <div
                                v-if="isLoadingWords"
                                class="flex items-center justify-center py-4"
                            >
                                <div
                                    class="h-4 w-4 animate-spin rounded-full border-b-2 border-primary"
                                ></div>
                                <span class="ml-2 text-sm text-muted-foreground">Loading more...</span>
                            </div>
                        </div>
                    </TabsContent>

                    <!-- Review Tab -->
                    <TabsContent value="review" class="mt-4">
                        <ReviewTab
                            ref="reviewTabRef"
                            :wordlist-id="currentWordlist.id"
                            @start-review="(words?: string[]) => { reviewSelectedWords = words; showReviewModal = true }"
                        />
                    </TabsContent>
                </Tabs>
            </div>

            <!-- No wordlist selected — show dashboard -->
            <div v-else-if="!isInitialLoading" key="empty">
                <WordlistDashboard />
            </div>
        </Transition>

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

        <!-- Word Detail Modal -->
        <WordDetailModal
            v-model="showDetailModal"
            :word="selectedWord"
            :wordlist-id="currentWordlist?.id ?? ''"
            @lookup="handleWordLookup"
            @review="handleStartReviewFromDetail"
            @edit="handleEdit"
            @remove="handleRemove"
        />

        <!-- Review Modal -->
        <ReviewModal
            v-if="currentWordlist"
            v-model="showReviewModal"
            :wordlist-id="currentWordlist.id"
            :wordlist-name="currentWordlist.name"
            :selected-words="reviewSelectedWords"
            @session-complete="handleReviewSessionComplete"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { useWindowVirtualizer } from '@tanstack/vue-virtual';
import { useElementSize, useDebounceFn } from '@vueuse/core';
import type { WordListItem, WordList } from '@/types';
import { wordlistApi } from '@/api';
import { useToast } from '@/components/ui/toast/use-toast';
import WordListCard from './WordListCard.vue';
import WordlistStatsBar from './WordlistStatsBar.vue';
import ReviewTab from './ReviewTab.vue';
import WordListUploadModal from './modals/WordListUploadModal.vue';
import CreateWordListModal from './modals/CreateWordListModal.vue';
import EditWordNotesModal from './modals/EditWordNotesModal.vue';
import ReviewModal from './modals/ReviewModal.vue';
import WordDetailModal from './modals/WordDetailModal.vue';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { applySortCriteria } from './utils/sortWords';
import { logger } from '@/utils/logger';
import EmptyState from '@/components/custom/definition/components/EmptyState.vue';
import WordlistDashboard from './WordlistDashboard.vue';

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
const activeTab = ref('words');
const isLoadingMeta = ref(false);
const isLoadingWords = ref(false);
const showUploadModal = ref(false);
const showCreateModal = ref(false);
const showEditNotesModal = ref(false);
const showReviewModal = ref(false);
const showDetailModal = ref(false);
const selectedWord = ref<WordListItem | null>(null);
const editingWord = ref<WordListItem | null>(null);
const currentWordlistData = ref<WordList | null>(null);
const currentPage = ref(0);
const reviewTabRef = ref<InstanceType<typeof ReviewTab> | null>(null);
const isChangingWordlist = ref(false);
const savedScrollPositions = ref<Record<string, number>>({ words: 0, review: 0 });
const reviewSelectedWords = ref<string[] | undefined>(undefined);

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
    const f = filters.value;
    const allMasteryShown = f.showBronze && f.showSilver && f.showGold;
    const noExtraFilters = !f.showHotOnly && !f.showDueOnly;

    // Fast path: no panel filters active
    let items: WordListItem[] = allMasteryShown && noExtraFilters
        ? wordlistMode.filteredResults as WordListItem[]
        : (() => {
            const now = f.showDueOnly ? Date.now() : 0;
            return (wordlistMode.filteredResults as WordListItem[]).filter((word: any) => {
                if (!allMasteryShown) {
                    if (word.mastery_level === 'bronze' && !f.showBronze) return false;
                    if (word.mastery_level === 'silver' && !f.showSilver) return false;
                    if (word.mastery_level === 'gold' && !f.showGold) return false;
                }
                if (f.showHotOnly && word.temperature !== 'hot') return false;
                if (f.showDueOnly) {
                    if (!word.review_data?.next_review_date) return false;
                    if (new Date(word.review_data.next_review_date).getTime() > now) return false;
                }
                return true;
            });
        })();

    // Apply sort criteria
    if (sortCriteria.value.length > 0) {
        items = applySortCriteria([...items], sortCriteria.value);
    }

    return items;
});

// ---------------------------------------------------------------------------
// Virtual scrolling: chunk words into rows based on container width
// ---------------------------------------------------------------------------

const gridContainer = ref<HTMLElement | null>(null);
const { width: containerWidth } = useElementSize(gridContainer);

const CARD_MIN_WIDTH = 140;
const GAP = 8; // matches gap-x-2 (0.5rem = 8px)
const columnCount = computed(() => {
    const w = containerWidth.value;
    if (w <= 0) return 2;
    return Math.max(1, Math.floor((w + GAP) / (CARD_MIN_WIDTH + GAP)));
});

const rows = computed(() => {
    const cols = columnCount.value;
    const items = currentWords.value;
    const result: WordListItem[][] = [];
    for (let i = 0; i < items.length; i += cols) {
        result.push(items.slice(i, i + cols));
    }
    return result;
});

const virtualizer = useWindowVirtualizer(computed(() => ({
    count: rows.value.length,
    estimateSize: () => 90,
    overscan: 5,
})));

const measureElement = (el: HTMLElement | null) => {
    if (el) {
        virtualizer.value.measureElement(el);
    }
};

// Automatic infinite scroll - load more when nearing the end
watch(
    () => {
        const items = virtualizer.value.getVirtualItems();
        return items[items.length - 1]?.index;
    },
    (lastIndex) => {
        if (
            lastIndex != null &&
            lastIndex >= rows.value.length - 3 &&
            hasMoreWords.value &&
            !isLoadingWords.value
        ) {
            loadMoreWords();
        }
    }
);

// Computed properties
const currentWordlist = computed(() => currentWordlistData.value);
const isInitialLoading = computed(() => (isLoadingMeta.value || isLoadingWords.value) && currentWords.value.length === 0);

const hasMoreWords = computed(() => {
    return wordlistMode.pagination.hasMore;
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
    selectedWord.value = word;
    showDetailModal.value = true;
};

const handleCardLookup = (word: WordListItem) => {
    searchBarStore.setMode('lookup');
    router.push({ name: 'Definition', params: { word: word.word } });
};

const handleWordLookup = (word: string) => {
    showDetailModal.value = false;
    searchBarStore.setMode('lookup');
    router.push({ name: 'Definition', params: { word } });
};

const handleStartReviewFromDetail = () => {
    showDetailModal.value = false;
    showReviewModal.value = true;
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
    showDetailModal.value = false;
    editingWord.value = word;
    showEditNotesModal.value = true;
};

const updateWordNotes = async (word: WordListItem, newNotes: string) => {
    try {
        if (!currentWordlist.value?.id) {
            logger.error('No wordlist selected');
            return;
        }

        // Persist to backend
        await wordlistApi.updateWord(currentWordlist.value.id, word.word, {
            notes: newNotes,
        });

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

        toast({ title: 'Notes updated', description: `Notes for "${word.word}" saved.` });
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
    reviewSelectedWords.value = undefined;
    // Refresh wordlist data after review session
    if (wordlistMode.selectedWordlist) {
        await loadWordlistMeta(wordlistMode.selectedWordlist);
        await triggerWordlistSearch();
        // Refresh review tab too
        reviewTabRef.value?.refresh();
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

// Simplified loading - delegates to orchestrator for API calls.
// Backend handles ALL filtering and sorting.
const triggerWordlistSearch = async () => {
    if (!wordlistMode.selectedWordlist) return;

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
            isChangingWordlist.value = true;
            currentPage.value = 0;
            activeTab.value = 'words';
            await loadWordlistMeta(newId);
            await triggerWordlistSearch();
            isChangingWordlist.value = false;
        } else {
            currentWordlistData.value = null;
        }
    },
    { immediate: true }
);

// Debounced search handler
const debouncedSearch = useDebounceFn(async () => {
    if (
        isChangingWordlist.value ||
        searchBarStore.searchMode !== 'wordlist' ||
        !wordlistMode.selectedWordlist
    ) {
        return;
    }
    await triggerWordlistSearch();
}, 300);

// Watch for search query changes
watch(
    () => searchBar.searchQuery,
    () => {
        debouncedSearch();
    }
);

// Save/restore scroll position per tab
watch(activeTab, (newTab, oldTab) => {
    if (oldTab) savedScrollPositions.value[oldTab] = window.scrollY;
    nextTick(() => window.scrollTo(0, savedScrollPositions.value[newTab] ?? 0));
});

// Reset selected review words when modal closes
watch(showReviewModal, (val) => {
    if (!val) reviewSelectedWords.value = undefined;
});
</script>

<style scoped>
/* Wordlist switch transition */
.wordlist-switch-enter-active {
    transition: opacity 200ms var(--ease-apple-smooth);
}
.wordlist-switch-leave-active {
    transition: opacity 150ms var(--ease-apple-smooth);
}
.wordlist-switch-enter-from,
.wordlist-switch-leave-to {
    opacity: 0;
}
</style>
