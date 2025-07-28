<template>
    <Transition
        enter-active-class="transition-all duration-350 ease-apple-elastic"
        leave-active-class="transition-all duration-200 ease-apple-bounce-in"
        enter-from-class="opacity-0 scale-90 translate-y-6 rotate-1"
        enter-to-class="opacity-100 scale-100 translate-y-0 rotate-0"
        leave-from-class="opacity-100 scale-100 translate-y-0 rotate-0"
        leave-to-class="opacity-0 scale-90 translate-y-6 rotate-1"
    >
        <div
            v-if="show"
            ref="searchResultsDropdown"
            class="dropdown-element cartoon-shadow-sm origin-top overflow-hidden rounded-2xl border-2 border-border bg-background/20 backdrop-blur-3xl"
            @mousedown.prevent
            @click="$emit('interaction')"
        >
            <!-- Loading State -->
            <div
                v-if="loading && results.length === 0 && !aiMode"
                class="p-4"
            >
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
                    <span class="text-sm text-muted-foreground">Searching...</span>
                </div>
            </div>

            <!-- Search Results -->
            <div
                v-else-if="results.length > 0"
                ref="searchResultsContainer"
                class="max-h-64 overflow-y-auto bg-background/20 backdrop-blur-3xl"
            >
                <button
                    v-for="(result, index) in results"
                    :key="result.word"
                    :ref="(el) => setResultRef(el as HTMLButtonElement, index)"
                    :class="[
                        'flex w-full items-center justify-between px-4 py-3 text-left transition-all duration-300 ease-apple-spring',
                        'border-muted-foreground/50 active:scale-[0.97]',
                        index === selectedIndex
                            ? 'scale-[1.02] border-l-8 bg-accent/60 pl-4 shadow-md'
                            : 'border-l-0 pl-4 hover:bg-accent/20 hover:scale-[1.01]',
                    ]"
                    @click="$emit('select-result', result)"
                    @mouseenter="selectedIndex = index"
                >
                    <span
                        :class="[
                            'transition-all duration-200',
                            index === selectedIndex && 'font-semibold text-primary',
                        ]"
                    >
                        {{ result.word }}
                    </span>
                    <div class="flex items-center gap-2 text-xs">
                        <span
                            :class="[
                                'text-muted-foreground',
                                index === selectedIndex && 'font-semibold text-primary',
                            ]"
                        >
                            {{ result.method }}
                        </span>
                        <span
                            :class="[
                                'text-muted-foreground',
                                index === selectedIndex && 'font-semibold text-primary',
                            ]"
                        >
                            {{ Math.round(result.score * 100) }}%
                        </span>
                    </div>
                </button>
            </div>

            <!-- No Results Messages -->
            <div
                v-else-if="!loading && query.length < 2"
                class="bg-background/50 p-4 text-center text-sm text-muted-foreground backdrop-blur-sm"
            >
                Type at least 2 characters to search...
            </div>
            <div
                v-else-if="!loading && query.length >= 2 && !aiMode"
                class="bg-background/50 p-4 text-center text-sm text-muted-foreground backdrop-blur-sm"
            >
                No matches found
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue';
import type { SearchResult } from '@/types';

interface SearchResultsProps {
    show: boolean;
    results: SearchResult[];
    loading: boolean;
    query: string;
    aiMode: boolean;
}

defineProps<SearchResultsProps>();

// Using defineModel for two-way binding of selectedIndex
const selectedIndex = defineModel<number>('selectedIndex', { required: true });

const emit = defineEmits<{
    'select-result': [result: SearchResult];
    'interaction': [];
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
    resultRefs
});
</script>