<template>
    <Transition
        name="dropdown"
    >
        <div
            v-if="show"
            ref="searchResultsDropdown"
            class="dropdown-element popover-surface origin-top overflow-hidden bg-background/96 border border-border/40 shadow-xl"
            @mousedown.prevent
            @click="$emit('interaction')"
        >
            <!-- Loading State -->
            <div v-if="loading && results.length === 0 && !aiMode" class="p-4">
                <div class="flex items-center gap-2">
                    <div class="flex gap-1">
                        <span
                            v-for="i in 3"
                            :key="i"
                            class="h-2 w-2 animate-bounce rounded-full bg-primary/60"
                            :style="{
                                animationDelay: `${(i - 1) * 150}ms`,
                            }"
                        />
                    </div>
                    <span class="text-sm text-muted-foreground"
                        >Searching...</span
                    >
                </div>
            </div>

            <!-- Unified Search Results -->
            <div
                v-else-if="results.length > 0"
                ref="searchResultsContainer"
                class="max-h-64 overflow-y-auto bg-transparent"
            >
                <SearchResultItem
                    v-for="(result, index) in results.slice(0, 10)"
                    :key="result.word"
                    :result="result"
                    :index="index"
                    :selected="index === selectedIndex"
                    @select="(r) => $emit('select-result', r)"
                    @hover="selectedIndex = $event"
                    @set-ref="setResultRef"
                />
            </div>

            <!-- Recent Searches (shown when query is empty and we have history) -->
            <div
                v-if="!loading && results.length === 0 && query.length === 0 && recentSearches && recentSearches.length > 0"
                class="max-h-64 overflow-y-auto bg-transparent"
            >
                <div class="px-4 py-2 text-xs font-medium text-muted-foreground/50 uppercase tracking-wider">Recent</div>
                <button
                    v-for="(search, index) in recentSearches.slice(0, 8)"
                    :key="search.query"
                    :class="[
                        'interactive-item ease-apple-spring flex w-full items-center border-l-4 border-transparent px-4 py-2.5 text-left transition-[background-color,color,box-shadow,transform] duration-250 transform-gpu',
                        'active:scale-[0.97]',
                        index === selectedIndex
                            ? 'border-l-primary/60 bg-accent/35 shadow-sm'
                            : 'hover:bg-accent/15 hover:shadow-sm',
                    ]"
                    @click="$emit('select-result', { word: search.query, score: 1.0, method: SearchMethod.EXACT })"
                    @mouseenter="selectedIndex = index"
                >
                    <span
                        :class="[
                            'transition-fast text-sm',
                            index === selectedIndex && 'font-semibold text-primary',
                        ]"
                    >
                        {{ search.query }}
                    </span>
                </button>
            </div>

            <!-- No Results Messages (only when there are truly no results) -->
            <div
                v-if="!loading && results.length === 0 && query.length < 2 && query.length > 0 && !aiMode && !(recentSearches && recentSearches.length > 0 && query.length === 0)"
                class="bg-transparent p-4 text-center text-sm text-muted-foreground"
            >
                Type at least 2 characters to search...
            </div>
            <div
                v-else-if="!loading && results.length === 0 && query.length >= 2 && !aiMode"
                class="bg-transparent p-4 text-center text-sm text-muted-foreground"
            >
                No matches found
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import { SearchMethod } from '@/types/api';
import SearchResultItem from './SearchResultItem.vue';

interface UnifiedResult {
    word: string;
    score: number;
    method?: string;
    matches?: Array<{ method: string; score: number }>;
    mastery_level?: string;
    frequency?: number;
    wordlist_id?: string;
    wordlist_name?: string;
}

interface SearchResultsProps {
    show: boolean;
    results: UnifiedResult[];
    loading: boolean;
    query: string;
    aiMode: boolean;
    recentSearches?: Array<{ query: string }>;
}

defineProps<SearchResultsProps>();

// Using defineModel for two-way binding of selectedIndex
const selectedIndex = defineModel<number>('selectedIndex', { required: true });

const emit = defineEmits<{
    'select-result': [result: any];
    interaction: [];
}>();

const searchResultsContainer = ref<HTMLDivElement>();
const searchResultsDropdown = ref<HTMLDivElement>();
const resultRefs = reactive<(HTMLButtonElement | null)[]>([]);

const setResultRef = (el: HTMLButtonElement | null, index: number) => {
    resultRefs[index] = el;
};

// Emit is used in template
void emit;

defineExpose({
    container: searchResultsContainer,
    element: searchResultsDropdown,
    resultRefs,
});
</script>

<style scoped>
/* dropdown transition classes are in src/assets/transitions.css */
</style>
