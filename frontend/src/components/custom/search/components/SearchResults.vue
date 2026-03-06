<template>
    <Transition
        name="results-dropdown"
    >
        <div
            v-if="show"
            ref="searchResultsDropdown"
            class="dropdown-element cartoon-shadow-sm origin-top overflow-hidden rounded-2xl border-2 border-border bg-background/20 backdrop-blur-3xl"
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

            <!-- Wordlist Search Results -->
            <div
                v-else-if="
                    wordlistMode &&
                    wordlistResults &&
                    wordlistResults.length > 0
                "
                ref="searchResultsContainer"
                class="max-h-64 overflow-y-auto bg-background/20 backdrop-blur-3xl"
            >
                <button
                    v-for="(result, index) in wordlistResults.slice(0, 10)"
                    :key="result.word"
                    :ref="(el) => setResultRef(el as HTMLButtonElement, index)"
                    :class="[
                        'ease-apple-spring flex w-full items-center justify-between px-4 py-3 text-left transition-all duration-300',
                        'border-muted-foreground/50 active:scale-[0.97]',
                        index === selectedIndex
                            ? 'scale-[1.02] border-l-8 bg-accent/60 pl-4 shadow-md'
                            : 'border-l-0 pl-4 hover:scale-[1.01] hover:bg-accent/20',
                    ]"
                    @click="$emit('select-result', { word: result.word, score: result.score || 1.0, method: SearchMethod.EXACT, is_phrase: false })"
                    @mouseenter="selectedIndex = index"
                >
                    <span
                        :class="[
                            'transition-all duration-200',
                            index === selectedIndex &&
                                'font-semibold text-primary',
                        ]"
                    >
                        {{ result.word.toLowerCase() }}
                    </span>
                    <div class="flex items-center gap-2 text-xs">
                        <span
                            :class="[
                                'inline-block rounded px-2 py-0.5',
                                result.mastery_level === 'gold' &&
                                    'bg-amber-300/10 text-amber-600 dark:text-amber-400',
                                result.mastery_level === 'silver' &&
                                    'bg-gray-300/10 text-gray-600 dark:text-gray-400',
                                result.mastery_level === 'bronze' &&
                                    'bg-orange-300/10 text-orange-600 dark:text-orange-400',
                                result.mastery_level === 'default' &&
                                    'bg-muted text-muted-foreground',
                                index === selectedIndex && 'font-semibold',
                            ]"
                        >
                            {{ result.mastery_level }}
                        </span>
                        <span
                            :class="[
                                'text-muted-foreground',
                                index === selectedIndex &&
                                    'font-semibold text-primary',
                            ]"
                        >
                            {{ result.frequency }}x
                        </span>
                        <span
                            :class="[
                                'font-medium text-muted-foreground',
                                index === selectedIndex &&
                                    'font-semibold text-primary',
                            ]"
                        >
                            {{ Math.round(result.score * 100) }}%
                        </span>
                    </div>
                </button>
            </div>

            <!-- Regular Search Results -->
            <div
                v-else-if="!wordlistMode && results.length > 0"
                ref="searchResultsContainer"
                class="max-h-64 overflow-y-auto bg-background/20 backdrop-blur-3xl"
            >
                <button
                    v-for="(result, index) in results"
                    :key="result.word"
                    :ref="(el) => setResultRef(el as HTMLButtonElement, index)"
                    :class="[
                        'ease-apple-spring flex w-full items-center justify-between px-4 py-3 text-left transition-all duration-300',
                        'border-muted-foreground/50 active:scale-[0.97]',
                        index === selectedIndex
                            ? 'scale-[1.02] border-l-8 bg-accent/60 pl-4 shadow-md'
                            : 'border-l-0 pl-4 hover:scale-[1.01] hover:bg-accent/20',
                    ]"
                    @click="$emit('select-result', result)"
                    @mouseenter="selectedIndex = index"
                >
                    <span
                        :class="[
                            'transition-all duration-200',
                            index === selectedIndex &&
                                'font-semibold text-primary',
                        ]"
                    >
                        {{ result.word }}
                    </span>
                    <div class="flex items-center gap-2 text-xs">
                        <span
                            :class="[
                                'text-muted-foreground',
                                index === selectedIndex &&
                                    'font-semibold text-primary',
                            ]"
                        >
                            {{ result.method }}
                        </span>
                        <span
                            :class="[
                                'text-muted-foreground',
                                index === selectedIndex &&
                                    'font-semibold text-primary',
                            ]"
                        >
                            {{ Math.round(result.score * 100) }}%
                        </span>
                    </div>
                </button>
            </div>

            <!-- Recent Searches (shown when query is empty and we have history) -->
            <div
                v-if="!loading && results.length === 0 && query.length === 0 && recentSearches && recentSearches.length > 0"
                class="max-h-64 overflow-y-auto bg-background/20 backdrop-blur-3xl"
            >
                <div class="px-4 py-2 text-xs font-medium text-muted-foreground/60 uppercase tracking-wider">Recent</div>
                <button
                    v-for="(search, index) in recentSearches.slice(0, 8)"
                    :key="search.query"
                    :class="[
                        'ease-apple-spring flex w-full items-center px-4 py-2.5 text-left transition-all duration-300',
                        'border-muted-foreground/50 active:scale-[0.97]',
                        index === selectedIndex
                            ? 'scale-[1.02] border-l-8 bg-accent/60 pl-4 shadow-md'
                            : 'border-l-0 pl-4 hover:scale-[1.01] hover:bg-accent/20',
                    ]"
                    @click="$emit('select-result', { word: search.query, score: 1.0, method: SearchMethod.EXACT, is_phrase: false })"
                    @mouseenter="selectedIndex = index"
                >
                    <span
                        :class="[
                            'transition-all duration-200 text-sm',
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
                class="bg-background/50 p-4 text-center text-sm text-muted-foreground backdrop-blur-sm"
            >
                Type at least 2 characters to search...
            </div>
            <div
                v-else-if="!loading && results.length === 0 && query.length >= 2 && !aiMode"
                class="bg-background/50 p-4 text-center text-sm text-muted-foreground backdrop-blur-sm"
            >
                {{
                    wordlistMode
                        ? 'No words found in wordlist'
                        : 'No matches found'
                }}
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import type { SearchResult } from '@/types';
import { SearchMethod } from '@/types/api';

interface SearchResultsProps {
    show: boolean;
    results: SearchResult[];
    loading: boolean;
    query: string;
    aiMode: boolean;
    wordlistMode?: boolean;
    wordlistResults?: any[];
    recentSearches?: Array<{ query: string }>;
}

defineProps<SearchResultsProps>();

// Using defineModel for two-way binding of selectedIndex
const selectedIndex = defineModel<number>('selectedIndex', { required: true });

const emit = defineEmits<{
    'select-result': [result: SearchResult];
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
/*
 * Results dropdown: split opacity (fast ease-out) from transform (elastic spring).
 * Opacity reaches 1 within the first ~40% of the animation so content is solid
 * while the transform spring is still resolving.
 */
.results-dropdown-enter-active {
    transition:
        opacity 180ms cubic-bezier(0.0, 0.0, 0.2, 1),
        transform 350ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}

.results-dropdown-leave-active {
    transition:
        opacity 150ms cubic-bezier(0.4, 0.0, 1, 1) 30ms,
        transform 200ms cubic-bezier(0.6, -0.28, 0.735, 0.045);
}

.results-dropdown-enter-from {
    opacity: 0;
    transform: scale(0.95) translateY(8px);
}

.results-dropdown-enter-to {
    opacity: 1;
    transform: scale(1) translateY(0);
}

.results-dropdown-leave-from {
    opacity: 1;
    transform: scale(1) translateY(0);
}

.results-dropdown-leave-to {
    opacity: 0;
    transform: scale(0.95) translateY(8px);
}
</style>
