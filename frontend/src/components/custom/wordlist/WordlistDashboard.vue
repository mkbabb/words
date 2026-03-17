<template>
    <div class="space-y-6">
        <!-- Header -->
        <div class="flex items-center justify-between">
            <div>
                <h2 class="font-serif text-2xl font-bold tracking-tight">Your Wordlists</h2>
                <p class="mt-0.5 text-sm text-muted-foreground/70">
                    {{ sortedWordlists.length }} {{ sortedWordlists.length === 1 ? 'list' : 'lists' }}
                </p>
            </div>
            <button
                @click="showCreate = true"
                class="glass-light inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium
                       transition-all duration-200 hover:shadow-sm hover:bg-background/90
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
                <Plus class="h-3.5 w-3.5" />
                New Wordlist
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
            v-else-if="sortedWordlists.length === 0"
            class="flex flex-col items-center justify-center rounded-2xl border border-dashed border-border/40
                   bg-background/40 backdrop-blur-sm px-6 py-16 text-center"
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
                class="glass-light mt-5 inline-flex items-center gap-1.5 rounded-full px-4 py-2 text-sm font-medium
                       transition-all duration-200 hover:shadow-sm hover:bg-background/90"
            >
                <Plus class="h-3.5 w-3.5" />
                Create a wordlist
            </button>
        </div>

        <!-- Wordlist grid -->
        <div v-else class="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <button
                v-for="wl in sortedWordlists"
                :key="wl.id"
                @click="selectWordlist(wl)"
                class="group relative overflow-hidden rounded-2xl border border-border/30 bg-background/60
                       p-5 text-left shadow-sm backdrop-blur-md transition-all duration-200
                       hover:border-border/50 hover:bg-background/80 hover:shadow-md
                       focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
                <!-- Subtle gradient overlay for glass depth -->
                <div
                    class="pointer-events-none absolute inset-0 rounded-2xl opacity-40
                           bg-gradient-to-br from-background/20 via-transparent to-muted/10"
                />

                <!-- Content -->
                <div class="relative">
                    <!-- Title row -->
                    <div class="flex items-start justify-between gap-2">
                        <h3 class="font-serif font-semibold leading-snug truncate">{{ wl.name }}</h3>
                        <span
                            v-if="wl.tags && wl.tags.length > 0"
                            class="shrink-0 rounded-full bg-muted/60 px-2 py-0.5 text-[10px] font-medium
                                   text-muted-foreground tracking-wide"
                        >
                            {{ wl.tags[0] }}
                        </span>
                    </div>

                    <!-- Description -->
                    <p
                        v-if="wl.description"
                        class="mt-1 line-clamp-2 text-xs text-muted-foreground/80 leading-relaxed"
                    >
                        {{ wl.description }}
                    </p>

                    <!-- Metadata row -->
                    <div class="mt-3 flex items-center gap-2.5 text-[11px] text-muted-foreground/60">
                        <span class="flex items-center gap-1">
                            <span class="tabular-nums font-medium text-foreground/70">{{ wl.unique_words ?? wl.total_words ?? 0 }}</span>
                            words
                        </span>
                        <span class="text-border">·</span>
                        <span v-if="lastAccessedLabel(wl)">{{ lastAccessedLabel(wl) }}</span>
                        <span v-else-if="wl.created_at">created {{ formatRelativeTime(wl.created_at) }}</span>
                    </div>

                    <!-- Mastery bar -->
                    <div class="mt-3.5 space-y-1">
                        <div class="h-1.5 w-full overflow-hidden rounded-full bg-muted/60 flex">
                            <!-- Mastered (gold/amber) -->
                            <div
                                class="h-full transition-all duration-500"
                                :style="{
                                    width: masteryBarWidth(wl, 'mastered') + '%',
                                    background: 'linear-gradient(90deg, hsl(43 90% 55%), hsl(43 80% 48%))',
                                }"
                            />
                            <!-- Familiar / in-progress (silver/gray) -->
                            <div
                                class="h-full transition-all duration-500"
                                :style="{
                                    width: masteryBarWidth(wl, 'familiar') + '%',
                                    background: 'linear-gradient(90deg, hsl(210 15% 65%), hsl(210 12% 55%))',
                                }"
                            />
                            <!-- Learning (orange) -->
                            <div
                                class="h-full transition-all duration-500"
                                :style="{
                                    width: masteryBarWidth(wl, 'learning') + '%',
                                    background: 'linear-gradient(90deg, hsl(25 85% 55%), hsl(25 75% 48%))',
                                }"
                            />
                        </div>
                        <!-- Legend pills (only if there's any data) -->
                        <div
                            v-if="hasMasteryData(wl)"
                            class="flex items-center gap-2 text-[10px] text-muted-foreground/50"
                        >
                            <span v-if="masteryCount(wl, 'mastered') > 0" class="flex items-center gap-1">
                                <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500/70" />
                                {{ masteryCount(wl, 'mastered') }} mastered
                            </span>
                            <span v-if="masteryCount(wl, 'learning') > 0" class="flex items-center gap-1">
                                <span class="inline-block h-1.5 w-1.5 rounded-full bg-orange-400/70" />
                                {{ masteryCount(wl, 'learning') }} learning
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Hover arrow indicator -->
                <div
                    class="absolute right-4 top-1/2 -translate-y-1/2 translate-x-2 opacity-0 transition-all
                           duration-200 group-hover:translate-x-0 group-hover:opacity-40"
                >
                    <ChevronRight class="h-4 w-4" />
                </div>
            </button>
        </div>

        <CreateWordListModal v-model="showCreate" @created="handleCreated" />
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { Plus, BookOpen, ChevronRight } from 'lucide-vue-next';
import CreateWordListModal from './modals/CreateWordListModal.vue';
import type { WordList } from '@/types';

const wordlistMode = useWordlistMode();
const searchBar = useSearchBarStore();
const router = useRouter();

const showCreate = ref(false);

const loading = computed(() => wordlistMode.wordlistsLoading);

/** Wordlists sorted by last_accessed desc, fallback updated_at, then created_at */
const sortedWordlists = computed(() => {
    const lists = wordlistMode.allWordlists as WordList[];
    return [...lists].sort((a, b) => {
        const dateA = a.last_accessed ?? a.updated_at ?? a.created_at ?? '';
        const dateB = b.last_accessed ?? b.updated_at ?? b.created_at ?? '';
        return dateB.localeCompare(dateA);
    });
});

function selectWordlist(wl: WordList) {
    wordlistMode.setWordlist(wl.id);
    searchBar.setMode('wordlist');
    router.push({ name: 'Wordlist', params: { wordlistId: wl.id } });
}

function handleCreated(wl: WordList) {
    wordlistMode.allWordlists = [wl, ...wordlistMode.allWordlists];
    selectWordlist(wl);
}

function formatRelativeTime(dateStr: string | null | undefined): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays === 0) return 'today';
    if (diffDays === 1) return 'yesterday';
    if (diffDays < 7) return `${diffDays}d ago`;
    if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
    return `${Math.floor(diffDays / 30)}mo ago`;
}

function lastAccessedLabel(wl: WordList): string {
    if (!wl.last_accessed) return '';
    return formatRelativeTime(wl.last_accessed);
}

/**
 * Mastery counts derived from words array when loaded,
 * falling back to learning_stats for summary views.
 */
function getMasteryCounts(wl: WordList) {
    if (wl.words && wl.words.length > 0) {
        const counts = { bronze: 0, silver: 0, gold: 0, default: 0 };
        for (const w of wl.words) {
            const lvl = (w as any).mastery_level ?? 'default';
            if (lvl in counts) (counts as any)[lvl]++;
        }
        return counts;
    }
    // Fallback: use learning_stats.words_mastered as gold proxy
    const mastered = wl.learning_stats?.words_mastered ?? 0;
    const total = wl.unique_words ?? wl.total_words ?? 0;
    const learning = Math.max(0, total - mastered);
    return { bronze: learning, silver: 0, gold: mastered, default: 0 };
}

function masteryCount(wl: WordList, bucket: 'mastered' | 'familiar' | 'learning'): number {
    const c = getMasteryCounts(wl);
    if (bucket === 'mastered') return c.gold;
    if (bucket === 'familiar') return c.silver;
    if (bucket === 'learning') return c.bronze;
    return 0;
}

function hasMasteryData(wl: WordList): boolean {
    const total = wl.unique_words ?? wl.total_words ?? 0;
    return total > 0;
}

function masteryBarWidth(wl: WordList, bucket: 'mastered' | 'familiar' | 'learning'): number {
    const total = wl.unique_words ?? wl.total_words ?? 0;
    if (!total) return 0;
    return (masteryCount(wl, bucket) / total) * 100;
}
</script>
