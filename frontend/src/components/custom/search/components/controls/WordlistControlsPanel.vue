<template>
    <!-- Dashboard mode: no wordlist selected — sort + tag controls -->
    <template v-if="!hasSelectedWordlist">
    <!-- Wordlists -->
    <div :class="sectionClass(true)">
        <h3 :class="headingClass">Wordlists</h3>
        <div class="flex flex-wrap gap-1.5 max-h-[4.5rem] overflow-y-auto scrollbar-thin">
            <button
                v-for="wl in recentWordlists"
                :key="wl.id"
                @click="navigateToWordlist(wl.id)"
                class="inline-flex items-center gap-1 rounded-md border border-border/40 bg-background/96 px-2.5 py-1 text-xs font-medium shadow-sm transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-spring select-none cursor-pointer hover:-translate-y-0.5 hover:bg-background hover:border-border/60 hover:shadow-md text-muted-foreground hover:text-foreground"
            >
                {{ wl.name }}
            </button>
        </div>
    </div>
    <hr :class="separatorClass" />
    <div v-if="dashboardTags.length > 0" :class="sectionClass()">
        <div class="flex items-center justify-between mb-2">
            <h3 :class="[headingClass, '!mb-0']">Filters</h3>
            <button
                v-if="activeDashboardTags.size > 0"
                @click="clearDashboardTags"
                class="p-0.5 rounded text-muted-foreground/40 hover:text-muted-foreground transition-colors"
                title="Reset filters"
            >
                <RotateCcw :size="12" />
            </button>
        </div>
        <div class="flex flex-wrap gap-1.5 max-h-[4.5rem] overflow-y-auto scrollbar-thin">
            <button
                v-for="tag in dashboardTags"
                :key="tag"
                @click="toggleDashboardTag(tag)"
                :class="[
                    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium shadow-sm transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-spring select-none cursor-pointer',
                    activeDashboardTags.has(tag)
                        ? 'bg-primary/15 text-primary ring-1 ring-primary/30'
                        : 'bg-background/96 text-muted-foreground ring-1 ring-border/30 hover:bg-background hover:text-foreground hover:shadow-md',
                ]"
            >
                <Tag :size="10" />
                {{ tag }}
            </button>
        </div>
    </div>
    <hr :class="separatorClass" />
    <div :class="sectionClass()">
        <h3 :class="headingClass">Sort</h3>
        <DashboardSortBuilder v-model="dashboardSortBy" :compact="compact" />
    </div>
    </template>

    <!-- Wordlist mode: show full mastery/filter/sort controls -->
    <template v-else>
    <!-- Filters (inline pills) -->
    <div :class="sectionClass(true)">
        <div class="flex items-center justify-between mb-2">
            <h3 :class="[headingClass, '!mb-0']">Filters</h3>
            <button
                v-if="hasNonDefaultFilters"
                @click="resetFilters"
                class="p-0.5 rounded text-muted-foreground/40 hover:text-muted-foreground transition-colors"
                title="Reset filters"
            >
                <RotateCcw :size="12" />
            </button>
        </div>
        <div class="flex flex-wrap gap-1.5">
            <button
                v-for="level in masteryButtons"
                :key="level.key"
                @click="toggleFilter(level.key)"
                :class="[
                    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium shadow-sm transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-spring select-none cursor-pointer',
                    (filtersValue as any)[level.key]
                        ? `${level.pillActiveClass} ring-1`
                        : 'bg-muted/30 text-muted-foreground ring-1 ring-border/30 hover:bg-background hover:text-muted-foreground hover:shadow-md',
                ]"
            >
                <span :class="['h-2 w-2 rounded-full flex-shrink-0', level.dotClass]" />
                {{ level.label }}
            </button>
            <button
                @click="toggleFilter('showHotOnly')"
                :class="[
                    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium shadow-sm transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-spring select-none cursor-pointer',
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
                    'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium shadow-sm transition-[background-color,border-color,color,box-shadow,transform] duration-200 ease-apple-spring select-none cursor-pointer',
                    filtersValue.showDueOnly
                        ? 'bg-blue-500/15 text-blue-500 ring-1 ring-blue-500/30'
                        : 'bg-muted/30 text-muted-foreground ring-1 ring-border/30 hover:bg-background hover:text-muted-foreground hover:shadow-md',
                ]"
            >
                <Clock :size="12" />
                Due
            </button>
        </div>
    </div>

    <!-- Separator -->
    <hr :class="separatorClass" />

    <!-- Search Mode -->
    <div :class="sectionClass()">
        <h3 :class="headingClass">Search</h3>
        <BouncyToggle
            :model-value="searchModeValue"
            @update:model-value="handleSearchModeChange"
            :options="searchModeOptions"
            class="text-sm font-medium"
        />
        <p class="mt-2 text-xs text-muted-foreground">
            {{ searchModeDescriptions[searchModeValue] }}
        </p>
    </div>

    <!-- Separator -->
    <hr :class="separatorClass" />

    <!-- Sort Order -->
    <div :class="sectionClass()">
        <div class="flex items-center justify-between mb-2">
            <h3 :class="[headingClass, '!mb-0']">Sort</h3>
            <button
                v-if="sortValue.length > 0"
                @click="resetSort"
                class="p-0.5 rounded text-muted-foreground/40 hover:text-muted-foreground transition-colors"
                title="Reset sort"
            >
                <RotateCcw :size="12" />
            </button>
        </div>
        <WordListSortBuilder v-model="sortValue" :compact="compact" />
    </div>
    </template>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Clock, Flame, RotateCcw, Tag } from 'lucide-vue-next';
import { DEFAULT_WORDLIST_FILTERS } from '@/stores/types/constants';
import WordListSortBuilder from '../../../wordlist/sorting/WordListSortBuilder.vue';
import DashboardSortBuilder from '../../../wordlist/sorting/DashboardSortBuilder.vue';
import { BouncyToggle } from '@/components/custom/animation';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useSearchBarStore } from '@/stores/search/search-bar';
import type { WordList } from '@/types';

const props = withDefaults(defineProps<{
    useStore?: boolean;
    compact?: boolean;
}>(), {
    useStore: false,
    compact: false,
});

const emit = defineEmits<{
    navigate: [];
}>();

const wordlistMode = useWordlistMode();
const searchBar = useSearchBarStore();

// Recent wordlists sorted by last_accessed (top 4)
const recentWordlists = computed(() =>
    [...(wordlistMode.allWordlists as WordList[])]
        .sort((a, b) => {
            const aDate = a.last_accessed ? new Date(a.last_accessed).getTime() : 0;
            const bDate = b.last_accessed ? new Date(b.last_accessed).getTime() : 0;
            return bDate - aDate;
        })
        .slice(0, 4)
);

function navigateToWordlist(id: string) {
    wordlistMode.setWordlist(id);
    searchBar.hideControls();
    emit('navigate');
}

const hasSelectedWordlist = computed(() => !!wordlistMode.selectedWordlist);

// Dashboard sort/tag state (shared via the wordlistMode store)
const dashboardSortBy = computed({
    get: () => wordlistMode.dashboardSortBy,
    set: (v: string) => wordlistMode.setDashboardSortBy(v),
});

const dashboardTags = computed(() => {
    const tags = new Set<string>();
    for (const wl of (wordlistMode.allWordlists as WordList[])) {
        if (wl.tags) for (const t of wl.tags) tags.add(t);
    }
    return Array.from(tags).sort();
});

const activeDashboardTags = computed(() => wordlistMode.dashboardSelectedTags);

function toggleDashboardTag(tag: string) {
    wordlistMode.toggleDashboardTag(tag);
}

function clearDashboardTags() {
    wordlistMode.dashboardSelectedTags = new Set();
}

// v-model bindings (used when useStore is false, i.e. from SearchControls)
const wordlistFiltersModel = defineModel<{
    showBronze: boolean;
    showSilver: boolean;
    showGold: boolean;
    showHotOnly: boolean;
    showDueOnly: boolean;
}>('wordlistFilters', {
    required: false,
    default: () => ({
        showBronze: true,
        showSilver: true,
        showGold: true,
        showHotOnly: false,
        showDueOnly: false,
    }),
});

const wordlistSortCriteriaModel = defineModel<any[]>('wordlistSortCriteria', {
    required: false,
    default: () => [],
});

// Computed refs that delegate to either store or v-model
const filtersValue = computed({
    get: () => props.useStore ? wordlistMode.wordlistFilters : wordlistFiltersModel.value,
    set: (val) => {
        if (props.useStore) {
            wordlistMode.setWordlistFilters(val);
        } else {
            wordlistFiltersModel.value = val;
        }
    },
});

const sortValue = computed({
    get: () => props.useStore ? [...wordlistMode.wordlistSortCriteria] as any[] : wordlistSortCriteriaModel.value,
    set: (val: any[]) => {
        if (props.useStore) {
            wordlistMode.setWordlistSortCriteria(val);
        } else {
            wordlistSortCriteriaModel.value = val;
        }
    },
});

const toggleFilter = (filterKey: string) => {
    const current = filtersValue.value;
    filtersValue.value = {
        ...current,
        [filterKey]: !(current as any)[filterKey],
    };
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

const resetFilters = () => {
    filtersValue.value = { ...DEFAULT_WORDLIST_FILTERS };
};

const resetSort = () => {
    sortValue.value = [];
};

// --- Search mode ---

const searchModeValue = computed(() => wordlistMode.searchMode);

const handleSearchModeChange = (mode: string | string[]) => {
    const val = Array.isArray(mode) ? mode[0] : mode;
    wordlistMode.setSearchMode(val as 'smart' | 'exact' | 'fuzzy' | 'semantic');
};

const searchModeOptions = [
    { label: 'Smart', value: 'smart', icon: 'Zap' },
    { label: 'Exact', value: 'exact', icon: 'Target' },
    { label: 'Fuzzy', value: 'fuzzy', icon: 'Sparkles' },
    { label: 'Semantic', value: 'semantic', icon: 'Search' },
];

const searchModeDescriptions: Record<string, string> = {
    smart: 'Adaptive search combining exact, fuzzy, and semantic matching',
    exact: 'Find exact word matches only',
    fuzzy: 'Find similar words and handle typos',
    semantic: 'Find words with similar meanings using AI',
};

// --- Styling helpers ---

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

// Compact mode (progressive sidebar) uses tighter spacing matching SidebarCluster aesthetic
const sectionClass = (first = false) =>
    props.compact
        ? `px-2 ${first ? 'pt-1' : ''} py-1.5`
        : `${first ? 'border-t border-border' : ''} px-4 py-3`;

const headingClass = computed(() =>
    props.compact
        ? 'mb-2 text-sm font-bold uppercase tracking-wider text-foreground/80'
        : 'mb-3 text-sm font-medium'
);

const separatorClass = computed(() =>
    props.compact
        ? 'my-1 border-0 h-px divider-h'
        : 'border-t border-border'
);
</script>
