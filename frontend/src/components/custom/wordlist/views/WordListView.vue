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
                        <p v-if="currentWordlist.description" class="mt-1 text-small font-serif text-muted-foreground line-clamp-2">
                            {{ currentWordlist.description }}
                        </p>
                    </div>
                    <GlassDock always-expanded class="flex-shrink-0">
                        <TooltipProvider :delay-duration="300">
                            <div class="flex items-center gap-1.5">
                                <Tooltip>
                                    <TooltipTrigger as-child>
                                        <button class="dock-icon-btn" @click="modals.showUploadModal.value = true"><Upload class="h-4 w-4" /></button>
                                    </TooltipTrigger>
                                    <TooltipContent>Upload words</TooltipContent>
                                </Tooltip>
                                <Tooltip>
                                    <TooltipTrigger as-child>
                                        <button class="dock-icon-btn" @click="modals.showCreateModal.value = true"><Plus class="h-4 w-4" /></button>
                                    </TooltipTrigger>
                                    <TooltipContent>Create wordlist</TooltipContent>
                                </Tooltip>
                                <div class="dock-separator" />
                                <Tooltip>
                                    <TooltipTrigger as-child>
                                        <button class="dock-icon-btn text-muted-foreground hover:text-destructive" @click="modals.showDeleteDialog.value = true"><Trash2 class="h-4 w-4" /></button>
                                    </TooltipTrigger>
                                    <TooltipContent>Delete wordlist</TooltipContent>
                                </Tooltip>
                            </div>
                        </TooltipProvider>
                    </GlassDock>
                </div>

                <!-- Stats row -->
                <div class="flex items-end gap-6 text-small">
                    <div>
                        <span class="text-heading font-bold font-serif tabular-nums">{{ formatCount(currentWordlist.unique_words) }}</span>
                        <span class="ml-1 text-muted-foreground">words</span>
                    </div>
                    <div v-if="masteryStats.gold > 0">
                        <span class="text-heading font-bold font-serif tabular-nums text-[var(--mastery-gold)]">{{ formatCount(masteryStats.gold) }}</span>
                        <span class="ml-1 text-muted-foreground">mastered</span>
                    </div>
                    <div v-if="dueForReview > 0">
                        <span class="text-heading font-bold font-serif tabular-nums text-primary">{{ formatCount(dueForReview) }}</span>
                        <span class="ml-1 text-muted-foreground">due</span>
                    </div>
                </div>

                <!-- Search indicator -->
                <div v-if="wordlistMode.currentQuery" class="flex items-center gap-2 text-sm text-muted-foreground">
                    <span class="font-medium tabular-nums">{{ cache.currentWords.value.length }} results</span>
                    <span class="text-muted-foreground/40">for</span>
                    <span class="font-medium text-foreground">"{{ wordlistMode.currentQuery }}"</span>
                </div>
            </ThemedCard>

            <!-- Word list (OUTSIDE card -- virtualizer manages scroll height) -->
            <div class="min-h-[50vh]">
                <!-- Empty State -->
                <div
                    v-if="cache.currentWords.value.length === 0 && !data.isLoadingWords.value && data.hasEverLoaded.value && !isInitialLoading"
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
                    :items="cache.currentWords.value"
                    :total-count="wordlistMode.pagination.total"
                    :window-start="wordlistMode.windowStart"
                    :is-loading="isInitialLoading || data.isLoadingWords.value"
                    :has-more="hasMoreWords"
                    @word-click="modals.handleWordClick"
                    @load-more="data.loadMoreWords"
                    @load-before="data.handleLoadBefore"
                />
            </div>

            <!-- Persistent bottom dock -->
            <Teleport to="body">
                <div class="fixed bottom-6 left-1/2 -translate-x-1/2 z-bar">
                    <GlassDock always-expanded>
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
                                    @click="modals.handleStartFullReview"
                                >
                                    Review {{ dueForReview }} Due
                                </Button>
                            </template>
                        </div>
                    </GlassDock>
                </div>
            </Teleport>
        </template>

            <!-- No wordlist selected -- show dashboard -->
            <div v-else-if="!isInitialLoading" key="empty">
                <WordlistDashboard />
            </div>

        <!-- File Upload Modal -->
        <WordListUploadModal
            v-if="modals.showUploadModal.value"
            v-model="modals.showUploadModal.value"
            :wordlist-id="currentWordlist?.id"
            @uploaded="data.handleWordsUploaded"
            @wordlists-updated="() => {}"
        />

        <!-- Create Wordlist Modal -->
        <CreateWordListModal
            v-if="modals.showCreateModal.value"
            v-model="modals.showCreateModal.value"
            @created="data.handleWordlistCreated"
        />

        <!-- Edit Word Notes Modal -->
        <EditWordNotesModal
            v-if="modals.showEditNotesModal.value"
            v-model="modals.showEditNotesModal.value"
            :word="modals.editingWord.value"
            @save="data.updateWordNotes"
        />

        <!-- Word Detail Modal -->
        <WordDetailModal
            v-if="modals.showDetailModal.value"
            v-model="modals.showDetailModal.value"
            :word="modals.selectedWord.value"
            :wordlist-id="currentWordlist?.id ?? ''"
            @lookup="data.handleWordLookup"
            @review="modals.handleStartReviewFromDetail"
            @edit="modals.handleEdit"
            @remove="data.handleRemove"
        />

        <!-- Review Modal -->
        <ReviewModal
            v-if="modals.showReviewModal.value && currentWordlist"
            v-model="modals.showReviewModal.value"
            :wordlist-id="currentWordlist.id"
            :wordlist-name="currentWordlist.name"
            :selected-words="modals.reviewSelectedWords.value"
            @session-complete="handleReviewSessionComplete"
        />

        <ConfirmDialog
            v-model:open="modals.showDeleteDialog.value"
            title="Delete Wordlist"
            :description="`Are you sure you want to delete &quot;${currentWordlist?.name ?? 'this wordlist'}&quot;? This action cannot be undone.`"
            confirm-label="Delete"
            :destructive="true"
            @confirm="data.handleDeleteWordlist"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, computed, defineAsyncComponent } from 'vue';
import { useStores } from '@/stores';
import { Plus, Trash2, Upload, X, ListChecks, CheckSquare } from 'lucide-vue-next';
import { Button, Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@mkbabb/glass-ui';
import { GlassDock, ConfirmDialog } from '@mkbabb/glass-ui';
import { ThemedCard } from '@/components/custom/card';
import { formatCount } from '../utils/formatting';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import WordListRows from '../list/WordList.vue';
import EmptyState from '@/components/custom/definition/components/EmptyState.vue';
import WordlistDashboard from './WordlistDashboard.vue';

// Composables
import { useWordListModals } from './composables/useWordListModals';
import { useWordListData } from './composables/useWordListData';
import { useWordListCache } from './composables/useWordListCache';

// Lazy-load heavy components that aren't needed on initial render
const WordListUploadModal = defineAsyncComponent(() => import('../modals/WordListUploadModal.vue'));
const CreateWordListModal = defineAsyncComponent(() => import('../modals/CreateWordListModal.vue'));
const EditWordNotesModal = defineAsyncComponent(() => import('../modals/EditWordNotesModal.vue'));
const ReviewModal = defineAsyncComponent(() => import('../modals/ReviewModal.vue'));
const WordDetailModal = defineAsyncComponent(() => import('../modals/WordDetailModal.vue'));

const { searchBar } = useStores();
const wordlistMode = useWordlistMode();

// Wire up the three composables
const modals = useWordListModals();
const data = useWordListData();
const cache = useWordListCache();

// Connect cache invalidation to wordlist-change lifecycle
data.onWordlistChange(() => cache.invalidateCache());

// Component ref for selection mode
const wordListRef = ref<InstanceType<typeof WordListRows> | null>(null);

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
    modals.handleReviewSelected(wordListRef.value?.selectedWords);
}

function handleReviewSessionComplete() {
    modals.reviewSelectedWords.value = undefined;
    data.handleReviewSessionComplete();
}

// Computed properties
const currentWordlist = computed(() => data.currentWordlistData.value);
const isInitialLoading = computed(() =>
    (data.isLoadingMeta.value || data.isLoadingWords.value) && cache.currentWords.value.length === 0,
);
const hasMoreWords = computed(() => wordlistMode.pagination.hasMore);

const masteryStats = computed(() => {
    const words = cache.currentWords.value;
    if (!words || words.length === 0) {
        return { bronze: 0, silver: 0, gold: 0 };
    }
    return words.reduce(
        (acc: Record<string, number>, word: any) => {
            acc[word.mastery_level] = (acc[word.mastery_level] || 0) + 1;
            return acc;
        },
        { bronze: 0, silver: 0, gold: 0 },
    );
});

const dueForReview = computed(() => data.preloadedDueCount.value ?? 0);
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
