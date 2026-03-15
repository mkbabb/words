<template>
    <!-- Mastery Levels -->
    <div class="border-t border-border/50 px-4 py-3">
        <h3 class="mb-3 text-sm font-medium">Mastery Levels</h3>
        <div class="flex flex-wrap gap-2">
            <button
                @click="toggleFilter('showBronze')"
                :class="[
                    'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ease-apple-spring select-none active:scale-[0.97]',
                    wordlistFilters.showBronze
                        ? 'bg-gradient-to-r from-orange-400 to-orange-600 text-white shadow-sm hover:scale-[1.05] hover:shadow-md'
                        : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03]',
                ]"
            >
                <div
                    class="h-2 w-2 rounded-full bg-gradient-to-r from-orange-400 to-orange-600"
                ></div>
                Learning
            </button>
            <button
                @click="toggleFilter('showSilver')"
                :class="[
                    'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ease-apple-spring select-none active:scale-[0.97]',
                    wordlistFilters.showSilver
                        ? 'bg-gradient-to-r from-gray-400 to-gray-600 text-white shadow-sm hover:scale-[1.05] hover:shadow-md'
                        : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03]',
                ]"
            >
                <div
                    class="h-2 w-2 rounded-full bg-gradient-to-r from-gray-400 to-gray-600"
                ></div>
                Familiar
            </button>
            <button
                @click="toggleFilter('showGold')"
                :class="[
                    'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ease-apple-spring select-none active:scale-[0.97]',
                    wordlistFilters.showGold
                        ? 'bg-gradient-to-r from-yellow-400 to-amber-600 text-white shadow-sm hover:scale-[1.05] hover:shadow-md'
                        : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03]',
                ]"
            >
                <div
                    class="h-2 w-2 rounded-full bg-gradient-to-r from-yellow-400 to-amber-600"
                ></div>
                Mastered
            </button>
        </div>
    </div>

    <!-- Additional Filters -->
    <div class="border-t border-border/50 px-4 py-3">
        <h3 class="mb-3 text-sm font-medium">Additional Filters</h3>
        <div class="flex flex-wrap gap-2">
            <button
                @click="toggleFilter('showHotOnly')"
                :class="[
                    'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ease-apple-spring select-none active:scale-[0.97]',
                    wordlistFilters.showHotOnly
                        ? 'bg-red-500 text-white shadow-sm hover:scale-[1.05] hover:bg-red-600 hover:shadow-md'
                        : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03]',
                ]"
            >
                <Flame :size="14" />
                Hot Only
            </button>
            <button
                @click="toggleFilter('showDueOnly')"
                :class="[
                    'flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all duration-200 ease-apple-spring select-none active:scale-[0.97]',
                    wordlistFilters.showDueOnly
                        ? 'bg-blue-500 text-white shadow-sm hover:scale-[1.05] hover:bg-blue-600 hover:shadow-md'
                        : 'bg-muted text-muted-foreground hover:bg-muted/70 hover:text-foreground hover:scale-[1.03]',
                ]"
            >
                <Clock :size="14" />
                Due for Review
            </button>
        </div>
    </div>

    <!-- Sort Order -->
    <div class="border-t border-border/50 px-4 py-3">
        <h3 class="mb-3 text-sm font-medium">Sort Order</h3>
        <WordListSortBuilder v-model="wordlistSortCriteria" />
    </div>
</template>

<script setup lang="ts">
import { Flame, Clock } from 'lucide-vue-next';
import WordListSortBuilder from '../../wordlist/WordListSortBuilder.vue';

const wordlistFilters = defineModel<{
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

const wordlistSortCriteria = defineModel<any[]>('wordlistSortCriteria', {
    required: false,
    default: () => [],
});

const toggleFilter = (filterKey: keyof typeof wordlistFilters.value) => {
    wordlistFilters.value = {
        ...wordlistFilters.value,
        [filterKey]: !wordlistFilters.value[filterKey],
    };
};
</script>
