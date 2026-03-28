<template>
    <div class="themed-card overflow-visible shadow-cartoon-lg bg-background/92 p-2 pt-3 rounded-xl">
        <!-- Instant swap — no transition. out-in doubles DOM during mode switch. -->
            <!-- Wordlist selected: show wordlist summary + controls -->
            <div v-if="currentWordlist" :key="'wl-' + currentWordlist.id" class="space-y-3">
                <!-- Wordlist name + back button -->
                <div class="flex items-start gap-2">
                    <button
                        @click="goBack"
                        class="glass-subtle p-1.5 rounded-xl text-muted-foreground hover:text-foreground hover:border-border/60 transition-[color,background-color,border-color,box-shadow] duration-200 ease-apple-default flex-shrink-0 shadow-sm hover:shadow-md"
                    >
                        <ChevronLeft class="h-4 w-4" />
                    </button>
                    <div class="min-w-0">
                        <h3 class="font-serif text-sm font-medium leading-tight truncate">
                            {{ currentWordlist.name }}
                        </h3>
                        <p class="text-micro text-muted-foreground/60 mt-0.5">
                            {{ formatCount(currentWordlist.unique_words ?? currentWordlist.total_words ?? 0) }} words
                        </p>
                    </div>
                </div>

                <!-- Mini mastery bar -->
                <div v-if="hasMastery" class="space-y-1.5">
                    <div class="h-1.5 w-full overflow-hidden rounded-full bg-muted/40 flex">
                        <div
                            class="h-full"
                            :style="{ width: goldPct + '%', background: 'var(--mastery-gold)' }"
                        />
                        <div
                            class="h-full"
                            :style="{ width: silverPct + '%', background: 'var(--mastery-silver)' }"
                        />
                        <div
                            class="h-full"
                            :style="{ width: bronzePct + '%', background: 'var(--mastery-bronze)' }"
                        />
                    </div>
                    <div class="flex justify-between text-[10px] text-muted-foreground/50 tabular-nums">
                        <span v-if="mastered > 0" class="flex items-center gap-1">
                            <span class="inline-block h-1.5 w-1.5 rounded-full" style="background: var(--mastery-gold)" />
                            {{ formatCount(mastered) }}
                        </span>
                        <span v-if="learning > 0" class="flex items-center gap-1">
                            <span class="inline-block h-1.5 w-1.5 rounded-full" style="background: var(--mastery-bronze)" />
                            {{ formatCount(learning) }}
                        </span>
                        <span v-if="newWords > 0" class="flex items-center gap-1">
                            <span class="inline-block h-1.5 w-1.5 rounded-full bg-muted" />
                            {{ formatCount(newWords) }}
                        </span>
                    </div>
                </div>

                <!-- Divider -->
                <div class="border-t border-border/30" />

                <!-- Controls (scrollable) -->
                <nav class="scrollbar-thin max-h-[calc(100dvh-14rem)] space-y-1 overflow-y-auto">
                    <!-- Filters dropdown -->
                    <div class="px-2 py-1">
                        <Popover>
                            <PopoverTrigger as-child>
                                <button class="flex w-full cursor-pointer select-none items-center gap-1.5 rounded-md border border-border/40 bg-background/96 px-2.5 py-1.5 text-sm font-medium shadow-sm transition-[background-color,border-color,box-shadow,transform] duration-250 ease-apple-spring hover:-translate-y-0.5 hover:bg-background hover:border-border/60 hover:shadow-md">
                                    <Filter :size="14" class="text-muted-foreground flex-shrink-0" />
                                    <span class="truncate">{{ filterLabel }}</span>
                                    <ChevronDown :size="14" class="ml-auto text-muted-foreground/50 flex-shrink-0" />
                                </button>
                            </PopoverTrigger>
                            <PopoverContent align="start" :side-offset="4" class="w-56 p-2">
                                <p class="px-1 pt-0.5 pb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">Mastery</p>
                                <div class="flex flex-wrap gap-1.5 mb-2">
                                    <button
                                        v-for="level in masteryButtons"
                                        :key="level.key"
                                        @click="toggleFilter(level.key)"
                                        :class="[
                                            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-spring select-none cursor-pointer shadow-sm',
                                            filtersValue[level.key as keyof typeof filtersValue]
                                                ? `${level.pillActiveClass} ring-1`
                                                : 'bg-muted/30 text-muted-foreground ring-1 ring-border/30 hover:bg-background hover:text-muted-foreground hover:shadow-md',
                                        ]"
                                    >
                                        <span :class="['h-2 w-2 rounded-full flex-shrink-0', level.dotClass]" />
                                        {{ level.label }}
                                    </button>
                                </div>
                                <div class="my-1.5 border-t border-border/30" />
                                <p class="px-1 pt-0.5 pb-1.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground/50">Status</p>
                                <div class="flex flex-wrap gap-1.5">
                                    <button
                                        @click="toggleFilter('showHotOnly')"
                                        :class="[
                                            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-spring select-none cursor-pointer shadow-sm',
                                            filtersValue.showHotOnly
                                                ? 'bg-red-500/15 text-red-500 ring-1 ring-red-500/30'
                                                : 'bg-muted/30 text-muted-foreground ring-1 ring-border/30 hover:bg-background hover:text-muted-foreground hover:shadow-md',
                                        ]"
                                    >
                                        <Flame :size="12" />
                                        Hot
                                    </button>
                                    <button
                                        @click="toggleFilter('showDueOnly')"
                                        :class="[
                                            'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-spring select-none cursor-pointer shadow-sm',
                                            filtersValue.showDueOnly
                                                ? 'bg-blue-500/15 text-blue-500 ring-1 ring-blue-500/30'
                                                : 'bg-muted/30 text-muted-foreground ring-1 ring-border/30 hover:bg-background hover:text-muted-foreground hover:shadow-md',
                                        ]"
                                    >
                                        <Clock :size="12" />
                                        Due
                                    </button>
                                </div>
                                <div v-if="hasNonDefaultFilters" class="mt-2 pt-1.5 border-t border-border/30">
                                    <button
                                        @click="resetFilters"
                                        class="flex items-center gap-1.5 text-xs text-muted-foreground/60 hover:text-muted-foreground transition-colors"
                                    >
                                        <RotateCcw :size="10" />
                                        Reset filters
                                    </button>
                                </div>
                            </PopoverContent>
                        </Popover>
                    </div>

                    <!-- Sort -->
                    <div class="px-2 py-1">
                        <div class="flex items-center justify-between mb-2">
                            <h3 class="text-sm font-medium uppercase tracking-wider text-foreground/80">Sort</h3>
                            <button
                                v-if="sortValue.length > 0"
                                @click="resetSort"
                                class="p-0.5 rounded text-muted-foreground/40 hover:text-muted-foreground transition-colors"
                                title="Reset sort"
                            >
                                <RotateCcw :size="12" />
                            </button>
                        </div>
                        <WordListSortBuilder v-model="sortValue" compact />
                    </div>
                </nav>
            </div>

            <!-- No wordlist: dashboard mode — sort/tags -->
            <div v-else key="dashboard" class="space-y-3">
                <!-- Tag filters dropdown -->
                <div v-if="dashboardTags.length > 0" class="px-2 py-1">
                    <Popover>
                        <PopoverTrigger as-child>
                                <button class="flex w-full cursor-pointer select-none items-center gap-1.5 rounded-md border border-border/40 bg-background/96 px-2.5 py-1.5 text-sm font-medium shadow-sm transition-[background-color,border-color,box-shadow,transform] duration-250 ease-apple-spring hover:-translate-y-0.5 hover:bg-background hover:border-border/60 hover:shadow-md">
                                <Filter :size="14" class="text-muted-foreground flex-shrink-0" />
                                <span class="truncate">{{ activeDashboardTags.size > 0 ? `${activeDashboardTags.size} tag${activeDashboardTags.size > 1 ? 's' : ''}` : 'All tags' }}</span>
                                <ChevronDown :size="14" class="ml-auto text-muted-foreground/50 flex-shrink-0" />
                            </button>
                        </PopoverTrigger>
                        <PopoverContent align="start" :side-offset="4" class="w-56 p-2 max-h-[10rem] overflow-y-auto scrollbar-thin">
                            <div class="flex flex-wrap gap-1.5">
                                <button
                                    v-for="tag in dashboardTags"
                                    :key="tag"
                                    @click="toggleDashboardTag(tag)"
                                    :class="[
                                        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-spring select-none cursor-pointer shadow-sm',
                                        activeDashboardTags.has(tag)
                                            ? 'bg-primary/15 text-primary ring-1 ring-primary/30'
                                            : 'bg-background/96 text-muted-foreground ring-1 ring-border/30 hover:bg-background hover:text-foreground hover:shadow-md',
                                    ]"
                                >
                                    <Tag :size="10" />
                                    {{ tag }}
                                </button>
                            </div>
                        </PopoverContent>
                    </Popover>
                </div>

                <!-- Sort -->
                <div class="px-2 py-1">
                    <h3 class="mb-2 text-sm font-medium uppercase tracking-wider text-foreground/80">Sort</h3>
                    <DashboardSortBuilder v-model="dashboardSortBy" compact />
                </div>
            </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import { ChevronDown, ChevronLeft, Clock, Filter, Flame, RotateCcw, Tag } from 'lucide-vue-next';
import { Popover, PopoverContent, PopoverTrigger } from '@mkbabb/glass-ui';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { DEFAULT_WORDLIST_FILTERS } from '@/stores/types/constants';
import WordListSortBuilder from '@/components/custom/wordlist/sorting/WordListSortBuilder.vue';
import DashboardSortBuilder from '@/components/custom/wordlist/sorting/DashboardSortBuilder.vue';
import type { WordList } from '@/types';
import { formatCount } from '@/components/custom/wordlist/utils/formatting';

const wordlistMode = useWordlistMode();
const router = useRouter();

const wordlists = computed(() => wordlistMode.allWordlists as WordList[]);

const currentWordlist = computed(() => {
    if (!wordlistMode.selectedWordlist) return null;
    const found = wordlists.value.find(wl => wl.id === wordlistMode.selectedWordlist);
    return found ?? null;
});

const total = computed(() => currentWordlist.value?.unique_words ?? currentWordlist.value?.total_words ?? 0);
const mastered = computed(() => currentWordlist.value?.learning_stats?.words_mastered ?? 0);
const learning = computed(() => Math.max(0, total.value - mastered.value));
const newWords = computed(() => {
    const t = total.value;
    if (!t) return 0;
    return Math.max(0, t - mastered.value);
});

const hasMastery = computed(() => total.value > 0);
const goldPct = computed(() => total.value ? (mastered.value / total.value) * 100 : 0);
const silverPct = computed(() => 0);
const bronzePct = computed(() => total.value ? (learning.value / total.value) * 100 : 0);

// Filters
const filtersValue = computed(() => wordlistMode.wordlistFilters);

const toggleFilter = (filterKey: string) => {
    wordlistMode.setWordlistFilters({
        ...filtersValue.value,
        [filterKey]: !(filtersValue.value as any)[filterKey],
    });
};

const hasNonDefaultFilters = computed(() => {
    const f = filtersValue.value;
    const d = DEFAULT_WORDLIST_FILTERS;
    return f.showBronze !== d.showBronze ||
        f.showSilver !== d.showSilver ||
        f.showGold !== d.showGold ||
        f.showHotOnly !== d.showHotOnly ||
        f.showDueOnly !== d.showDueOnly;
});

const filterLabel = computed(() => {
    if (!hasNonDefaultFilters.value) return 'All words';
    let count = 0;
    const f = filtersValue.value;
    if (!f.showBronze) count++;
    if (!f.showSilver) count++;
    if (!f.showGold) count++;
    if (f.showHotOnly) count++;
    if (f.showDueOnly) count++;
    return `${count} active`;
});

const resetFilters = () => {
    wordlistMode.setWordlistFilters({ ...DEFAULT_WORDLIST_FILTERS });
};

// Sort
const sortValue = computed({
    get: () => [...wordlistMode.wordlistSortCriteria] as any[],
    set: (val: any[]) => wordlistMode.setWordlistSortCriteria(val),
});

const resetSort = () => {
    sortValue.value = [];
};

// Dashboard state
const dashboardSortBy = computed({
    get: () => wordlistMode.dashboardSortBy,
    set: (v: string) => wordlistMode.setDashboardSortBy(v),
});

const dashboardTags = computed(() => {
    const tags = new Set<string>();
    for (const wl of wordlists.value) {
        if (wl.tags) for (const t of wl.tags) tags.add(t);
    }
    return Array.from(tags).sort();
});

const activeDashboardTags = computed(() => wordlistMode.dashboardSelectedTags);

function toggleDashboardTag(tag: string) {
    wordlistMode.toggleDashboardTag(tag);
}

const masteryButtons = [
    {
        key: 'showBronze',
        label: 'Learning',
        pillActiveClass: 'bg-orange-500/15 text-orange-500 ring-orange-500/30',
        dotClass: 'bg-gradient-to-r from-orange-400 to-orange-600',
    },
    {
        key: 'showSilver',
        label: 'Familiar',
        pillActiveClass: 'bg-gray-400/15 text-gray-500 ring-gray-400/30',
        dotClass: 'bg-gradient-to-r from-gray-400 to-gray-600',
    },
    {
        key: 'showGold',
        label: 'Mastered',
        pillActiveClass: 'bg-amber-500/15 text-amber-500 ring-amber-500/30',
        dotClass: 'bg-gradient-to-r from-yellow-400 to-amber-600',
    },
];

function goBack() {
    wordlistMode.setWordlist(null);
    router.push({ name: 'Home' });
}
</script>

