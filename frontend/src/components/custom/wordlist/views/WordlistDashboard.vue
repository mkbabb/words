<template>
    <div class="space-y-6">
        <!-- Header: inline title + big stats -->
        <div class="flex items-baseline justify-between gap-4">
            <div class="flex items-baseline gap-4">
                <h2 class="text-heading tracking-tight">Your Wordlists</h2>
                <span class="text-sm text-muted-foreground/50">
                    {{ filteredWordlists.length }} {{ filteredWordlists.length === 1 ? 'list' : 'lists' }}
                </span>
            </div>
            <button
                @click="showCreate = true"
                class="glass-subtle inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium
                       transition-fast hover:shadow-sm hover:bg-background/90
                       focus-ring"
            >
                <Plus class="h-3.5 w-3.5" />
                New
            </button>
        </div>

        <!-- Big Stats Row -->
        <div class="flex items-end gap-8">
            <div>
                <p class="tabular-nums font-serif text-4xl font-bold tracking-tight leading-none">
                    {{ formatCount(globalStats?.global_stats?.total_words ?? totalWordsAcrossLists) }}
                </p>
                <p class="mt-1 text-xs text-muted-foreground/60 uppercase tracking-widest">unique words</p>
            </div>
            <div>
                <p class="tabular-nums font-serif text-4xl font-bold tracking-tight leading-none mastery-gold">
                    {{ formatCount(globalStats?.global_stats?.words_mastered ?? totalMasteredAcrossLists) }}
                </p>
                <p class="mt-1 text-xs text-muted-foreground/60 uppercase tracking-widest">mastered</p>
            </div>
            <div v-if="globalStreakDays > 0">
                <p class="tabular-nums font-serif text-4xl font-bold tracking-tight leading-none mastery-bronze flex items-end gap-1.5">
                    <Flame class="h-7 w-7 mb-0.5" />
                    {{ formatCount(globalStreakDays) }}
                </p>
                <p class="mt-1 text-xs text-muted-foreground/60 uppercase tracking-widest">day streak</p>
            </div>
        </div>

        <!-- Active filters summary (sort/tag controls live in controls dropdown + progressive sidebar) -->
        <div v-if="selectedTags.size > 0" class="flex items-center gap-2 text-xs text-muted-foreground/60">
            <span>Filtering by:</span>
            <button
                v-for="tag in Array.from(selectedTags)"
                :key="tag"
                @click="toggleTagFilter(tag)"
                class="rounded-full px-2 py-0.5 text-xs font-medium bg-primary/10 text-primary hover:bg-primary/20 transition-colors"
            >
                {{ tag }} ×
            </button>
        </div>

        <!-- Loading skeleton -->
        <div v-if="loading" class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <div
                v-for="i in 6"
                :key="i"
                class="h-36 animate-pulse rounded-2xl bg-muted/30"
            />
        </div>

        <!-- Empty state -->
        <div
            v-else-if="allWordlists.length === 0"
            class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border/40
                   glass-subtle px-6 py-16 text-center"
        >
            <div class="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-muted/50">
                <BookOpen class="h-7 w-7 text-muted-foreground/50" />
            </div>
            <p class="font-serif text-lg font-semibold">No wordlists yet</p>
            <p class="mt-1.5 max-w-xs text-sm text-muted-foreground/70">
                Build your vocabulary one list at a time — create your first wordlist to get started.
            </p>
            <button
                @click="showCreate = true"
                class="glass-subtle mt-5 inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium
                       transition-fast hover:shadow-sm hover:bg-background/90"
            >
                <Plus class="h-3.5 w-3.5" />
                Create a wordlist
            </button>
        </div>

        <!-- No matching results -->
        <div
            v-else-if="filteredWordlists.length === 0"
            class="flex flex-col items-center justify-center rounded-2xl glass-subtle px-6 py-12 text-center"
        >
            <BookOpen class="mb-3 h-8 w-8 text-muted-foreground/30" />
            <p class="font-serif text-base font-semibold">No matching wordlists</p>
            <p class="mt-1 text-sm text-muted-foreground/70">
                Try clearing your tag filters.
            </p>
        </div>

        <!-- Aggregate word search results (across all wordlists) -->
        <div v-if="aggregateResults.length > 0 && searchQuery" class="space-y-3">
            <h3 class="text-xs font-medium uppercase tracking-widest text-muted-foreground/50">
                Words matching "{{ searchQuery }}"
            </h3>
            <div class="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <button
                    v-for="item in aggregateResults.slice(0, 12)"
                    :key="`${item.wordlist_id}-${item.word}`"
                    class="flex items-center justify-between rounded-xl px-4 py-2.5 text-left text-sm
                           transition-fast hover:bg-accent/20 active:scale-[0.98]
                           border border-border/30"
                    @click="item.wordlist_id && navigateToWordInList(item.wordlist_id, item.word)"
                >
                    <span class="font-medium">{{ item.word }}</span>
                    <div class="flex items-center gap-2 text-xs text-muted-foreground">
                        <span
                            v-if="item.mastery_level"
                            :class="[
                                'rounded-full px-1.5 py-0.5',
                                item.mastery_level === 'gold' && 'bg-amber-300/10 text-amber-600',
                                item.mastery_level === 'silver' && 'bg-gray-300/10 text-gray-600',
                                item.mastery_level === 'bronze' && 'bg-orange-300/10 text-orange-600',
                                item.mastery_level === 'default' && 'bg-muted',
                            ]"
                        >{{ item.mastery_level }}</span>
                        <span class="max-w-[100px] truncate text-muted-foreground/50">{{ item.wordlist_name }}</span>
                        <span class="tabular-nums">{{ item.score != null ? Math.round(item.score * 100) + '%' : '' }}</span>
                    </div>
                </button>
            </div>
        </div>

        <!-- Wordlist grid -->
        <WordlistGrid
            :wordlists="filteredWordlists"
            @select="selectWordlist"
            @delete="promptDeleteWordlist"
        />

        <CreateWordListModal v-if="showCreate" v-model="showCreate" @created="handleCreated" />

        <ConfirmDialog
            v-if="showDeleteDialog"
            v-model:open="showDeleteDialog"
            title="Delete Wordlist"
            :description="`Are you sure you want to delete &quot;${wordlistToDelete?.name ?? 'this wordlist'}&quot;? This action cannot be undone.`"
            confirm-label="Delete"
            :destructive="true"
            @confirm="confirmDeleteWordlist"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, defineAsyncComponent } from 'vue';
import { useRouter } from 'vue-router';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useAuthStore } from '@/stores/auth';
import { usersApi } from '@/api/users';
import { wordlistApi } from '@/api/wordlists';
import { Plus, BookOpen, Flame } from 'lucide-vue-next';
import { useToast, ConfirmDialog } from '@mkbabb/glass-ui';

import WordlistGrid from '../WordlistGrid.vue';
const CreateWordListModal = defineAsyncComponent(() => import('../modals/CreateWordListModal.vue'));
import type { WordList } from '@/types';
import type { WordListSearchItem } from '@/types/wordlist';
import { formatCount } from '../utils/formatting';
import { logger } from '@/utils/logger';

const wordlistMode = useWordlistMode();
const searchBar = useSearchBarStore();
const auth = useAuthStore();
const router = useRouter();
const { toast } = useToast();

const showCreate = ref(false);
const showDeleteDialog = ref(false);
const wordlistToDelete = ref<WordList | null>(null);

// Aggregate cross-wordlist search results
const aggregateResults = ref<WordListSearchItem[]>([]);
const aggregateLoading = ref(false);

// Watch search query for aggregate search
let aggregateDebounce: ReturnType<typeof setTimeout> | null = null;
watch(
    () => searchBar.searchQuery,
    (q) => {
        const trimmed = q?.trim() ?? '';
        if (aggregateDebounce) clearTimeout(aggregateDebounce);
        if (trimmed.length < 2) {
            aggregateResults.value = [];
            return;
        }
        aggregateDebounce = setTimeout(async () => {
            aggregateLoading.value = true;
            try {
                const response = await wordlistApi.searchAllWordlists(trimmed, { limit: 30 });
                aggregateResults.value = (response.items || []) as WordListSearchItem[];
            } catch {
                aggregateResults.value = [];
            } finally {
                aggregateLoading.value = false;
            }
        }, 300);
    },
);

// Sort/tag state lives in the store so controls dropdown + progressive sidebar can access it
const sortBy = computed({
    get: () => wordlistMode.dashboardSortBy as 'last_accessed' | 'name' | 'word_count' | 'mastery',
    set: (v: string) => wordlistMode.setDashboardSortBy(v),
});
const selectedTags = computed(() => wordlistMode.dashboardSelectedTags);

// Global stats
const globalStats = ref<any>(null);
const statsLoading = ref(false);

const loading = computed(() => wordlistMode.wordlistsLoading);
const allWordlists = computed(() => wordlistMode.allWordlists as WordList[]);

function toggleTagFilter(tag: string) {
    wordlistMode.toggleDashboardTag(tag);
}

/** Search query from the universal search bar */
const searchQuery = computed(() => searchBar.searchQuery?.trim().toLowerCase() ?? '');

/** Filtered and sorted wordlists */
const filteredWordlists = computed(() => {
    let lists = [...allWordlists.value];

    // Filter by search query (from universal search bar)
    if (searchQuery.value) {
        const q = searchQuery.value;
        lists = lists.filter(wl =>
            wl.name.toLowerCase().includes(q) ||
            wl.description?.toLowerCase().includes(q) ||
            wl.tags?.some(t => t.toLowerCase().includes(q))
        );
    }

    // Filter by tags
    if (selectedTags.value.size > 0) {
        lists = lists.filter(wl =>
            wl.tags && wl.tags.some(t => selectedTags.value.has(t))
        );
    }

    // Sort
    lists.sort((a, b) => {
        switch (sortBy.value) {
            case 'name':
                return a.name.localeCompare(b.name);
            case 'word_count':
                return (b.unique_words || 0) - (a.unique_words || 0);
            case 'mastery':
                return (b.learning_stats?.words_mastered || 0) - (a.learning_stats?.words_mastered || 0);
            default: {
                // last_accessed
                const dateA = a.last_accessed ?? a.updated_at ?? a.created_at ?? '';
                const dateB = b.last_accessed ?? b.updated_at ?? b.created_at ?? '';
                return dateB.localeCompare(dateA);
            }
        }
    });

    return lists;
});

/** Aggregate stats from local data when API stats unavailable */
const totalWordsAcrossLists = computed(() =>
    allWordlists.value.reduce((sum, wl) => sum + (wl.unique_words ?? wl.total_words ?? 0), 0)
);

const totalMasteredAcrossLists = computed(() =>
    allWordlists.value.reduce((sum, wl) => sum + (wl.learning_stats?.words_mastered ?? 0), 0)
);

const globalStreakDays = computed(() => {
    if (globalStats.value?.global_stats?.streak_days) {
        return globalStats.value.global_stats.streak_days;
    }
    // Fallback: max streak across lists
    return allWordlists.value.reduce((max, wl) =>
        Math.max(max, wl.learning_stats?.streak_days ?? 0), 0
    );
});

async function fetchGlobalStats() {
    if (!auth.isAuthenticated) return;
    statsLoading.value = true;
    try {
        globalStats.value = await usersApi.getLearningStats();
    } catch {
        // silent fail — stats bar just won't show
    } finally {
        statsLoading.value = false;
    }
}

async function selectWordlist(wl: WordList) {
    wordlistMode.setWordlist(wl.id);
    await searchBar.setMode('wordlist');
    router.push({ name: 'Wordlist', params: { wordlistId: wl.id } });
}

async function navigateToWordInList(wordlistId: string, word: string) {
    wordlistMode.setWordlist(wordlistId);
    await searchBar.setMode('wordlist');
    searchBar.setQuery(word);
    router.push({ name: 'Wordlist', params: { wordlistId } });
}

function handleCreated(wl: WordList) {
    wordlistMode.allWordlists = [wl, ...wordlistMode.allWordlists];
    selectWordlist(wl);
}

function promptDeleteWordlist(wl: WordList) {
    wordlistToDelete.value = wl;
    showDeleteDialog.value = true;
}

async function confirmDeleteWordlist() {
    if (!wordlistToDelete.value) return;
    const target = wordlistToDelete.value;
    try {
        await wordlistApi.deleteWordlist(target.id);
        wordlistMode.setAllWordlists(allWordlists.value.filter((wl) => wl.id !== target.id));
        if (wordlistMode.selectedWordlist === target.id) {
            wordlistMode.setWordlist(null);
            router.push({ name: 'Home' });
        }
        showDeleteDialog.value = false;
        wordlistToDelete.value = null;
        toast({
            title: 'Wordlist deleted',
            description: `"${target.name}" was deleted.`,
        });
    } catch (error) {
        logger.error('Failed to delete wordlist:', error);
        toast({
            title: 'Error',
            description: 'Failed to delete wordlist.',
            variant: 'destructive',
        });
    } finally {
        showDeleteDialog.value = false;
        wordlistToDelete.value = null;
    }
}

onMounted(() => {
    fetchGlobalStats();
});
</script>
