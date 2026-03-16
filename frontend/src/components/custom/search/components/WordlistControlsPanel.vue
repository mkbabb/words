<template>
    <!-- Mastery Levels -->
    <div :class="sectionClass(true)">
        <h3 :class="headingClass">Mastery</h3>
        <div :class="compact ? 'flex gap-2' : 'flex flex-wrap gap-1.5'">
            <button
                v-for="level in masteryButtons"
                :key="level.key"
                @click="toggleFilter(level.key)"
                :title="level.label"
                :class="compact
                    ? [
                        'flex items-center justify-center rounded-full h-7 w-7 transition-all duration-200 ease-apple-spring select-none active:scale-[0.92]',
                        (filtersValue as any)[level.key]
                            ? `${level.activeClass} shadow-sm ring-2 ring-primary/20`
                            : 'bg-muted/40 opacity-40 hover:opacity-70 hover:scale-110',
                      ]
                    : [
                        chipBase,
                        (filtersValue as any)[level.key]
                            ? `${level.activeClass} text-white shadow-sm`
                            : chipInactive,
                      ]
                "
            >
                <div v-if="compact" :class="['h-3 w-3 rounded-full', (filtersValue as any)[level.key] ? 'bg-white' : level.dotClass]" />
                <template v-else>
                    <div :class="['h-2 w-2 rounded-full', level.dotClass]" />
                    {{ level.label }}
                </template>
            </button>
        </div>
    </div>

    <!-- Separator -->
    <hr :class="separatorClass" />

    <!-- Additional Filters -->
    <div :class="sectionClass()">
        <h3 :class="headingClass">Filters</h3>
        <div class="flex flex-wrap gap-1.5">
            <button
                @click="toggleFilter('showHotOnly')"
                :class="[
                    chipBase,
                    filtersValue.showHotOnly
                        ? 'bg-red-500 text-white shadow-sm'
                        : chipInactive,
                ]"
            >
                <Flame :size="compact ? 14 : 14" />
                Hot
            </button>
            <button
                @click="toggleFilter('showDueOnly')"
                :class="[
                    chipBase,
                    filtersValue.showDueOnly
                        ? 'bg-blue-500 text-white shadow-sm'
                        : chipInactive,
                ]"
            >
                <Clock :size="compact ? 14 : 14" />
                Due
            </button>
        </div>
    </div>

    <!-- Separator -->
    <hr :class="separatorClass" />

    <!-- Sort Order -->
    <div :class="sectionClass()">
        <h3 :class="headingClass">Sort</h3>
        <WordListSortBuilder v-model="sortValue" :compact="compact" />
    </div>

    <!-- Reset All (bottom, always visible) -->
    <hr :class="separatorClass" />
    <div :class="sectionClass()" class="flex items-center">
        <button
            @click="resetAll"
            :disabled="!hasNonDefaultState"
            :class="[
                chipBase,
                hasNonDefaultState
                    ? 'bg-destructive/10 text-destructive hover:bg-destructive/20'
                    : 'bg-muted/30 text-muted-foreground/40 cursor-not-allowed',
            ]"
        >
            <RotateCcw :size="compact ? 14 : 14" />
            Reset All
        </button>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Flame, Clock, RotateCcw } from 'lucide-vue-next';
import { DEFAULT_WORDLIST_FILTERS } from '@/stores/types/constants';
import WordListSortBuilder from '../../wordlist/WordListSortBuilder.vue';
import { useWordlistMode } from '@/stores/search/modes/wordlist';

const props = withDefaults(defineProps<{
    useStore?: boolean;
    compact?: boolean;
}>(), {
    useStore: false,
    compact: false,
});

const wordlistMode = useWordlistMode();

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

const hasNonDefaultState = computed(() => {
    const f = filtersValue.value;
    const d = DEFAULT_WORDLIST_FILTERS;
    const filtersChanged =
        f.showBronze !== d.showBronze ||
        f.showSilver !== d.showSilver ||
        f.showGold !== d.showGold ||
        f.showHotOnly !== d.showHotOnly ||
        f.showDueOnly !== d.showDueOnly;
    const sortChanged = sortValue.value.length > 0;
    return filtersChanged || sortChanged;
});

const resetAll = () => {
    filtersValue.value = { ...DEFAULT_WORDLIST_FILTERS };
    sortValue.value = [];
};

// --- Styling helpers ---

const masteryButtons = [
    {
        key: 'showBronze',
        label: 'Learning',
        activeClass: 'bg-gradient-to-r from-orange-400 to-orange-600',
        dotClass: 'bg-gradient-to-r from-orange-400 to-orange-600',
    },
    {
        key: 'showSilver',
        label: 'Familiar',
        activeClass: 'bg-gradient-to-r from-gray-400 to-gray-600',
        dotClass: 'bg-gradient-to-r from-gray-400 to-gray-600',
    },
    {
        key: 'showGold',
        label: 'Mastered',
        activeClass: 'bg-gradient-to-r from-yellow-400 to-amber-600',
        dotClass: 'bg-gradient-to-r from-yellow-400 to-amber-600',
    },
];

// Compact mode (progressive sidebar) uses tighter spacing matching SidebarCluster aesthetic
const sectionClass = (first = false) =>
    props.compact
        ? `px-2 ${first ? 'pt-1' : ''} py-1.5`
        : `${first ? 'border-t border-border/50' : ''} px-4 py-3`;

const headingClass = computed(() =>
    props.compact
        ? 'mb-2 text-sm font-bold uppercase tracking-wider text-foreground/80'
        : 'mb-3 text-sm font-medium'
);

const separatorClass = computed(() =>
    props.compact
        ? 'my-1 border-0 h-px bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent dark:via-muted-foreground/30'
        : 'border-t border-border/50'
);

const chipBase = computed(() =>
    props.compact
        ? 'flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-all duration-200 ease-apple-spring select-none active:scale-[0.97]'
        : 'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ease-apple-spring select-none active:scale-[0.97]'
);

const chipInactive = computed(() =>
    props.compact
        ? 'bg-muted/50 text-muted-foreground hover:bg-muted/70 hover:text-foreground'
        : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03]'
);
</script>
