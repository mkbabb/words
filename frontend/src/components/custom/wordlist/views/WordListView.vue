<template>
    <div class="space-y-3">
        <!-- Wordlist content -->
        <template v-if="currentWordlist" :key="currentWordlist?.id ?? 'dashboard'">
            <!-- Header card -->
            <ThemedCard
                :variant="'default'"
                class-name="space-y-4 p-4 sm:p-5"
                texture-enabled
                texture-type="clean"
                texture-intensity="subtle"
                hide-star
            >
                <!-- Title row -->
                <div class="flex items-start justify-between gap-4">
                    <div class="min-w-0">
                        <h1 class="text-title truncate">{{ currentWordlist.name }}</h1>
                        <p v-if="currentWordlist.description" class="mt-0.5 text-sm font-serif text-muted-foreground line-clamp-2">
                            {{ currentWordlist.description }}
                        </p>
                    </div>
                    <GlassDock :start-collapsed="false" manual>
                        <TooltipProvider :delay-duration="300">
                            <div class="flex items-center gap-1.5">
                                <Tooltip>
                                    <TooltipTrigger as-child>
                                        <button class="dock-icon-btn" @click="showUploadModal = true"><Upload class="h-4 w-4" /></button>
                                    </TooltipTrigger>
                                    <TooltipContent>Upload words</TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                    <TooltipTrigger as-child>
                                        <button class="dock-icon-btn" @click="showCreateModal = true"><Plus class="h-4 w-4" /></button>
                                    </TooltipTrigger>
                                    <TooltipContent>Create wordlist</TooltipContent>
                                </Tooltip>
                                <div class="dock-separator" />
                                <Tooltip>
                                    <TooltipTrigger as-child>
                                        <button class="dock-icon-btn text-muted-foreground hover:text-destructive" @click="showDeleteDialog = true"><Trash2 class="h-4 w-4" /></button>
                                    </TooltipTrigger>
                                    <TooltipContent>Delete wordlist</TooltipContent>
                                </Tooltip>
                            </div>
                        </TooltipProvider>
                    </GlassDock>
                </div>

                <!-- Stats row -->
                <div class="flex items-end gap-6 text-sm">
                    <div>
                        <span class="text-2xl font-bold font-serif tabular-nums">{{ formatCount(currentWordlist.unique_words) }}</span>
                        <span class="ml-1 text-muted-foreground">words</span>
                    </div>
                    <div v-if="masteryStats.gold > 0">
                        <span class="text-2xl font-bold font-serif tabular-nums text-[var(--mastery-gold)]">{{ formatCount(masteryStats.gold) }}</span>
                        <span class="ml-1 text-muted-foreground">mastered</span>
                    </div>
                    <div v-if="dueForReview > 0">
                        <span class="text-2xl font-bold font-serif tabular-nums text-primary">{{ formatCount(dueForReview) }}</span>
                        <span class="ml-1 text-muted-foreground">due</span>
                    </div>
                </div>

                <!-- Search indicator -->
                <div v-if="wordlistMode.currentQuery" class="flex items-center gap-2 text-sm text-muted-foreground">
                    <span class="font-medium tabular-nums">{{ currentWords.length }} results</span>
                    <span class="text-muted-foreground/40">for</span>
                    <span class="font-medium text-foreground">"{{ wordlistMode.currentQuery }}"</span>
                </div>
            </ThemedCard>

            <!-- Word list (OUTSIDE card — virtualizer manages scroll height) -->
            <div class="min-h-[50vh]">
                <!-- Empty State -->
                <div
                    v-if="currentWords.length === 0 && !isLoadingWords && hasEverLoaded && !isInitialLoading"
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

                <!-- Virtualized row list -->
                <WordListRows
                    v-else
                    ref="wordListRef"
                    :items="currentWords"
                    :total-count="wordlistMode.pagination.total"
                    :window-start="wordlistMode.windowStart"
                    :is-loading="isInitialLoading || isLoadingWords"
                    :has-more="hasMoreWords"
                    @word-click="handleWordClick"
                    @load-more="loadMoreWords"
                    @load-before="handleLoadBefore"
                />
            </div>

            <!-- Persistent bottom dock -->
            <Teleport to="body">
                <div class="fixed bottom-6 left-1/2 -translate-x-1/2 z-bar">
                    <GlassDock :start-collapsed="false" manual>
                        <div class="flex items-center gap-1.5">
                            <!-- Review mode toggle -->
                            <Button
                                :variant="isReviewMode ? 'default' : 'ghost'"
                                size="sm"
                                class="h-10 rounded-full px-4"
                                @click="toggleReviewMode"
                            >
                                <CheckSquare :size="16" class="mr-1.5" />
                                {{ isReviewMode ? 'Exit Select' : 'Select' }}
                            </Button>

                            <!-- Selection actions (visible in review mode) -->
                            <template v-if="isReviewMode">
                                <div class="h-6 w-px bg-border/50 shrink-0" />
                                <button
                                    class="flex h-10 w-10 items-center justify-center rounded-full bg-card border border-border/30 transition-colors duration-150 hover:bg-background/80 text-muted-foreground hover:text-foreground"
                                    @click="selectAllWords"
                                    title="Select all"
                                >
                                    <ListChecks :size="16" />
                                </button>
                                <button
                                    v-if="selectionCount > 0"
                                    class="flex h-10 w-10 items-center justify-center rounded-full bg-card border border-border/30 transition-colors duration-150 hover:bg-background/80 text-muted-foreground hover:text-foreground"
                                    @click="clearSelection"
                                    title="Clear selection"
                                >
                                    <X :size="16" />
                                </button>
                                <Button
                                    v-if="selectionCount > 0"
                                    size="sm"
                                    class="h-10 rounded-full px-5"
                                    @click="handleReviewSelected"
                                >
                                    Review ({{ selectionCount }})
                                </Button>
                            </template>

                            <!-- Due count (visible when not in review mode) -->
                            <template v-if="!isReviewMode && dueForReview > 0">
                                <div class="h-6 w-px bg-border/50 shrink-0" />
                                <Button
                                    size="sm"
                                    class="h-10 rounded-full px-5"
                                    @click="handleStartFullReview"
                                >
                                    Review {{ dueForReview }} Due
                                </Button>
                            </template>
                        </div>
                    </GlassDock>
                </div>
            </Teleport>
        </template>

            <!-- No wordlist selected — show dashboard -->
            <div v-else-if="!isInitialLoading" key="empty">
                <WordlistDashboard />
            </div>

        <!-- File Upload Modal -->
        <WordListUploadModal
            v-if="showUploadModal"
            v-model="showUploadModal"
            :wordlist-id="currentWordlist?.id"
            @uploaded="handleWordsUploaded"
            @wordlists-updated="() => {}"
        />

        <!-- Create Wordlist Modal -->
        <CreateWordListModal
            v-if="showCreateModal"
            v-model="showCreateModal"
            @created="handleWordlistCreated"
        />

        <!-- Edit Word Notes Modal -->
        <EditWordNotesModal
            v-if="showEditNotesModal"
            v-model="showEditNotesModal"
            :word="editingWord"
            @save="updateWordNotes"
        />

        <!-- Word Detail Modal -->
        <WordDetailModal
            v-if="showDetailModal"
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
            v-if="showReviewModal && currentWordlist"
            v-model="showReviewModal"
            :wordlist-id="currentWordlist.id"
            :wordlist-name="currentWordlist.name"
            :selected-words="reviewSelectedWords"
            @session-complete="handleReviewSessionComplete"
        />

        <ConfirmDialog
            v-model:open="showDeleteDialog"
            title="Delete Wordlist"
            :description="`Are you sure you want to delete &quot;${currentWordlist?.name ?? 'this wordlist'}&quot;?`"
            message="This action cannot be undone. All words and progress will be permanently deleted."
            confirm-text="Delete"
            cancel-text="Cancel"
            :destructive="true"
            @confirm="handleDeleteWordlist"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, shallowRef, computed, watch, defineAsyncComponent } from 'vue';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { Plus, Trash2, Upload, X, ListChecks, CheckSquare } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import { useDebounceFn } from '@vueuse/core';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import { GlassDock } from '@/components/custom/animation';
import { ThemedCard } from '@/components/custom/card';
import type { WordListItem, WordList } from '@/types';
import { wordlistApi } from '@/api';
import { useToast } from '@/components/ui/toast/use-toast';
import WordListRows from '../list/WordList.vue';
import { formatCount } from '../utils/formatting';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useWordlistSearch } from '@/components/custom/search/composables/useWordlistSearch';
import { applySortCriteria } from '../utils/sortWords';
import { logger } from '@/utils/logger';
import EmptyState from '@/components/custom/definition/components/EmptyState.vue';
import WordlistDashboard from './WordlistDashboard.vue';
import ConfirmDialog from '../../ConfirmDialog.vue';

// Lazy-load heavy components that aren't needed on initial render
const WordListUploadModal = defineAsyncComponent(() => import('../modals/WordListUploadModal.vue'));
const CreateWordListModal = defineAsyncComponent(() => import('../modals/CreateWordListModal.vue'));
const EditWordNotesModal = defineAsyncComponent(() => import('../modals/EditWordNotesModal.vue'));
const ReviewModal = defineAsyncComponent(() => import('../modals/ReviewModal.vue'));
const WordDetailModal = defineAsyncComponent(() => import('../modals/WordDetailModal.vue'));

const { searchBar } = useStores();
const wordlistMode = useWordlistMode();
const searchBarStore = useSearchBarStore();
const router = useRouter();

// Wordlist-specific search operations (no lookup composable overhead)
const wordlistSearch = useWordlistSearch();
const { toast } = useToast();

// Component state
const isLoadingMeta = ref(false);
const isLoadingWords = ref(false);
const showUploadModal = ref(false);
const showCreateModal = ref(false);
const showEditNotesModal = ref(false);
const showReviewModal = ref(false);
const showDetailModal = ref(false);
const showDeleteDialog = ref(false);
const selectedWord = ref<WordListItem | null>(null);
const editingWord = ref<WordListItem | null>(null);
const currentWordlistData = ref<WordList | null>(null);
const currentPage = ref(0);
const wordListRef = ref<InstanceType<typeof WordListRows> | null>(null);
const isChangingWordlist = ref(false);
const reviewSelectedWords = ref<string[] | undefined>(undefined);
const hasEverLoaded = ref(false);
const preloadedDueCount = ref<number | null>(null);

// Selection state
const selectionCount = computed(() => wordListRef.value?.selectedWords?.size ?? 0);
const isReviewMode = computed(() => wordListRef.value?.reviewMode ?? false);

function toggleReviewMode() {
    if (wordListRef.value?.reviewMode) {
        wordListRef.value.clearSelection();
    } else {
        wordListRef.value?.enterReviewMode();
    }
}

function clearSelection() {
    wordListRef.value?.clearSelection();
}

function selectAllWords() {
    wordListRef.value?.selectAll();
}

function handleReviewSelected() {
    const sel = wordListRef.value?.selectedWords;
    reviewSelectedWords.value = sel ? Array.from(sel) : undefined;
    showReviewModal.value = true;
}

function handleStartFullReview() {
    reviewSelectedWords.value = undefined;
    showReviewModal.value = true;
}

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
// Debounced grid rendering: the card grid reads from a cached snapshot that
// updates on a trailing debounce so rapid keystrokes don't thrash the
// virtualizer or cause repeated row measurement.
// ---------------------------------------------------------------------------

const renderCache = shallowRef(new Map<string, WordListItem[]>());

const cacheKey = computed(() => {
    const query = searchBar.searchQuery.trim().toLowerCase();
    return [
        wordlistMode.selectedWordlist ?? 'none',
        wordlistMode.resultsVersion,
        query,
        filters.value.showBronze,
        filters.value.showSilver,
        filters.value.showGold,
        filters.value.showHotOnly,
        filters.value.showDueOnly,
        wordlistMode.filters.minScore,
        sortCriteria.value
            .map((criterion) =>
                'key' in criterion
                    ? `${criterion.key}:${criterion.order}`
                    : `${criterion.field}:${criterion.direction}`
            )
            .join(','),
    ].join('|');
});

/**
 * Apply the wordlist panel's boolean filters (showBronze, showSilver, etc.)
 * on top of the store's filteredResults, then sort.
 */
function computeFilteredWords(): WordListItem[] {
    const key = cacheKey.value;
    const cached = renderCache.value.get(key);
    if (cached) return cached;

    const f = filters.value;
    const allMasteryShown = f.showBronze && f.showSilver && f.showGold;
    const noExtraFilters = !f.showHotOnly && !f.showDueOnly;

    let items: WordListItem[] = allMasteryShown && noExtraFilters
        ? (wordlistMode.filteredResults as WordListItem[])
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

    if (sortCriteria.value.length > 0) {
        items = applySortCriteria([...items], sortCriteria.value);
    }

    const snapshot = [...items] as WordListItem[];
    renderCache.value.set(key, snapshot);
    if (renderCache.value.size > 24) {
        const firstKey = renderCache.value.keys().next().value;
        if (firstKey) renderCache.value.delete(firstKey);
    }
    return snapshot;
}

// The debounced snapshot that the grid actually renders from.
// Updated via a debounced watcher so rapid search keystrokes don't cause
// the virtualizer + card components to re-render on every keystroke.
const debouncedWords = shallowRef<WordListItem[]>([]);

const flushGridWords = useDebounceFn(() => {
    debouncedWords.value = computeFilteredWords();
}, 120);

// Watch all inputs that affect the grid and debounce the update
watch(
    [
        () => wordlistMode.filteredResults,
        filters,
        sortCriteria,
        () => wordlistMode.resultsVersion,
        () => searchBar.searchQuery,
        () => wordlistMode.selectedWordlist,
    ],
    () => {
        flushGridWords();
    },
    { immediate: true }
);

// Expose the debounced list as `currentWords` so the rest of the component
// (virtualizer, rows, stats, empty state) reads from the stable snapshot.
const currentWords = computed(() => debouncedWords.value);

watch(
    () => searchBarStore.searchMode,
    (mode, previousMode) => {
        if (mode === 'wordlist' && wordlistMode.selectedWordlist) {
            triggerWordlistSearch();
        } else if (previousMode === 'wordlist' && mode !== 'wordlist') {
            searchBar.hideDropdown();
        }
    }
);

watch(
    () => wordlistMode.searchMode,
    () => {
        if (searchBarStore.searchMode === 'wordlist' && wordlistMode.selectedWordlist) {
            triggerWordlistSearch();
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

// Due count from backend stats (preloaded separately from word data)
const dueForReview = computed(() => preloadedDueCount.value ?? 0);

// ---------------------------------------------------------------------------
// Methods
// ---------------------------------------------------------------------------

const handleWordClick = (word: WordListItem) => {
    selectedWord.value = word;
    showDetailModal.value = true;
};

const handleWordLookup = async (word: string) => {
    showDetailModal.value = false;
    await searchBarStore.setMode('lookup');
    searchBarStore.setQuery(word);
    router.push({ name: 'Definition', params: { word } });
};

const handleStartReviewFromDetail = () => {
    showDetailModal.value = false;
    showReviewModal.value = true;
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

const handleDeleteWordlist = async () => {
    if (!currentWordlist.value?.id) return;
    const wordlistName = currentWordlist.value.name;

    try {
        await wordlistApi.deleteWordlist(currentWordlist.value.id);
        wordlistMode.setWordlist(null);
        currentWordlistData.value = null;
        showDeleteDialog.value = false;
        router.push({ name: 'Home' });
        toast({ title: 'Wordlist deleted', description: `"${wordlistName}" was deleted.` });
    } catch (error) {
        logger.error('Failed to delete wordlist:', error);
        toast({
            title: 'Error',
            description: 'Failed to delete wordlist.',
            variant: 'destructive',
        });
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
        // Refresh word list after review
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
        // Fetch metadata and stats in parallel
        const [response, stats] = await Promise.all([
            wordlistApi.getWordlist(id),
            wordlistApi.getStatistics(id).catch(() => null),
        ]);

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

        // Use backend-computed due count (accurate for full wordlist)
        // Stats API returns { data: { word_counts: { due_for_review } } } (REST envelope)
        const statsData = (stats as any)?.data ?? stats;
        preloadedDueCount.value = statsData?.word_counts?.due_for_review ?? 0;
    } catch (error) {
        logger.error('Failed to load wordlist metadata:', error);
        // Clear selection so dashboard shows properly
        wordlistMode.setWordlist(null);
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
    wordlistMode.setCurrentQuery(query);

    isLoadingWords.value = true;
    try {
        if (!query) {
            await wordlistSearch.executeWordlistFetch(wordlistId);
            searchBar.hideDropdown();
        } else {
            const results = await wordlistSearch.executeWordlistSearchApi(
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
        hasEverLoaded.value = true;
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
        await wordlistSearch.loadMoreWordlist();
    } catch (error) {
        logger.error('Failed to load more words:', error);
    } finally {
        isLoadingWords.value = false;
    }
};

const handleLoadBefore = (offset: number) => {
    wordlistSearch.loadBeforeWordlist(offset);
};

// Watch for wordlist changes
watch(
    () => wordlistMode.selectedWordlist,
    async (newId) => {
        if (newId) {
            isChangingWordlist.value = true;
            hasEverLoaded.value = false;
            currentPage.value = 0;
            // Clear stale results immediately so the grid doesn't render
            // 1000+ cards from a previous session while we fetch fresh data.
            wordlistMode.clearResults();
            debouncedWords.value = [];
            renderCache.value = new Map();
            await loadWordlistMeta(newId);
            await triggerWordlistSearch();
            isChangingWordlist.value = false;
        } else {
            currentWordlistData.value = null;
        }
    },
    { immediate: true }
);

// Debounce the API call itself so we don't fire on every keystroke,
// but keep it short (150ms) so the dropdown feels responsive.
// The grid rendering is separately debounced via debouncedWords (150ms).
const debouncedApiSearch = useDebounceFn(async () => {
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
    (newQuery, oldQuery) => {
        if (
            isChangingWordlist.value ||
            searchBarStore.searchMode !== 'wordlist' ||
            !wordlistMode.selectedWordlist
        ) {
            return;
        }

        const trimmed = newQuery.trim();

        // Empty query: immediately clear dropdown and refetch all words
        if (!trimmed) {
            searchBar.hideDropdown();
            if (oldQuery?.trim()) {
                triggerWordlistSearch();
            }
            return;
        }

        // Non-empty query: short debounce on the API call;
        // the grid re-render is separately debounced via the debouncedWords watcher.
        debouncedApiSearch();
    }
);

// Tab switch — no scroll jump, content fades via CSS transition.

// Reset selected review words when modal closes
watch(showReviewModal, (val) => {
    if (!val) reviewSelectedWords.value = undefined;
});
</script>

<style scoped>
/* Tab content fade transition */
.tab-fade-enter-active,
.tab-fade-leave-active {
    transition: opacity 0.15s ease;
}
.tab-fade-enter-from,
.tab-fade-leave-to {
    opacity: 0;
}

/* Dock icon buttons (mirror GlassDock scoped styles) */
.dock-icon-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2rem;
    height: 2rem;
    border-radius: 9999px;
    border: none;
    background: transparent;
    color: var(--color-muted-foreground);
    cursor: pointer;
    transition: color 0.15s ease, background-color 0.15s ease;
    padding: 0;
}
.dock-icon-btn:hover {
    background: color-mix(in srgb, var(--color-foreground) 8%, transparent);
    color: var(--color-foreground);
    transform: scale(1.1);
}
.dock-separator {
    width: 1px;
    height: 1.5rem;
    background: color-mix(in srgb, var(--color-foreground) 20%, transparent);
    flex-shrink: 0;
}
</style>
