<template>
    <!-- Loading skeleton -->
    <div v-if="isLoading && items.length === 0" class="wordlist-paper rounded-2xl border bg-card overflow-hidden shadow-cartoon-sm">
        <div
            v-for="i in 8"
            :key="i"
            class="flex items-center gap-4 px-4 sm:px-6 py-3 wordlist-paper__line"
        >
            <div class="flex-1 space-y-1.5">
                <div class="h-4 w-32 rounded bg-muted animate-pulse" />
                <div class="h-3 w-20 rounded bg-muted/50 animate-pulse" />
            </div>
            <div class="h-3 w-10 rounded-full bg-muted/40 animate-pulse" />
        </div>
    </div>

    <!-- Word list — virtualized rows.
         Mobile: 1 column (single-word rows).
         Desktop (lg+): 2 columns (paired words per virtual row). -->
    <div v-else class="wordlist-paper rounded-2xl border bg-card overflow-hidden shadow-cartoon-sm">
        <div :style="{ height: `${totalSize}px`, position: 'relative', width: '100%' }">
            <div
                v-for="vRow in virtualRows"
                :key="vRow.index"
                class="wordlist-paper__row"
                :class="{ 'wordlist-paper__line': vRow.index > 0 }"
                :style="{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    height: `${rowHeight}px`,
                    transform: `translateY(${vRow.start}px)`,
                }"
            >
                <div
                    class="grid h-full"
                    :style="{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }"
                >
                    <template v-for="col in columns" :key="col">
                        <template v-if="getItemForCell(vRow.index, col - 1)">
                            <WordListRow
                                :word="getItemForCell(vRow.index, col - 1)!"
                                :index="vRow.index * columns + (col - 1)"
                                :is-selected="selectedWords.has(getItemForCell(vRow.index, col - 1)!.word)"
                                :class="col > 1 ? 'border-l border-border/15' : ''"
                                @click="(w, idx, ev) => handleRowClick(w, idx, ev)"
                            />
                        </template>
                        <!-- Skeleton for evicted/unloaded slots -->
                        <div
                            v-else-if="(vRow.index * columns + (col - 1)) < totalCount"
                            :class="['flex items-center gap-4 px-4 sm:px-6 py-3', col > 1 ? 'border-l border-border/15' : '']"
                        >
                            <div class="flex-1 space-y-1.5">
                                <div class="h-4 w-32 rounded bg-muted animate-pulse" />
                                <div class="h-3 w-20 rounded bg-muted/50 animate-pulse" />
                            </div>
                        </div>
                    </template>
                </div>
            </div>
        </div>

        <!-- Loading more indicator -->
        <div
            v-if="isLoading && items.length > 0"
            class="flex items-center justify-center py-3 wordlist-paper__line"
        >
            <div class="h-3.5 w-3.5 animate-spin rounded-full border-b-2 border-primary" />
            <span class="ml-2 text-xs text-muted-foreground">Loading more...</span>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useWindowVirtualizer } from '@tanstack/vue-virtual';
import { useMediaQuery } from '@vueuse/core';
import type { WordListItem } from '@/types';
import WordListRow from './WordListRow.vue';

const props = withDefaults(defineProps<{
    items: WordListItem[];
    totalCount: number;
    windowStart?: number;
    isLoading?: boolean;
    hasMore?: boolean;
}>(), {
    windowStart: 0,
    isLoading: false,
    hasMore: false,
});

const emit = defineEmits<{
    'word-click': [word: WordListItem, event: MouseEvent];
    'load-more': [];
    'load-before': [offset: number];
}>();

// ─── Responsive columns ──────────────────────────────────────────
// Mobile (<lg): 1 column. Desktop (lg+ ≥1024px): 2 columns.
const isLg = useMediaQuery('(min-width: 1024px)');
const columns = computed(() => (isLg.value ? 2 : 1));

// ─── Selection (managed here, exposed to parent) ─────────────────
const selectedWords = ref<Set<string>>(new Set());
const lastClickedIndex = ref(-1);
const reviewMode = ref(false);

function handleRowClick(word: WordListItem, index: number, event: MouseEvent) {
    if (reviewMode.value) {
        if (event.shiftKey && lastClickedIndex.value >= 0) {
            const start = Math.min(lastClickedIndex.value, index);
            const end = Math.max(lastClickedIndex.value, index);
            const next = new Set(selectedWords.value);
            for (let i = start; i <= end && i < props.items.length; i++) {
                const w = itemAt(i);
                if (w) next.add(w.word);
            }
            selectedWords.value = next;
        } else if (event.metaKey || event.ctrlKey) {
            const next = new Set(selectedWords.value);
            if (next.has(word.word)) next.delete(word.word);
            else next.add(word.word);
            selectedWords.value = next;
        } else {
            const next = new Set(selectedWords.value);
            if (next.has(word.word)) next.delete(word.word);
            else next.add(word.word);
            selectedWords.value = next;
        }
        lastClickedIndex.value = index;
    } else {
        emit('word-click', word, event);
    }
}

function selectAll() {
    selectedWords.value = new Set(props.items.map(i => i.word));
}

function clearSelection() {
    selectedWords.value = new Set();
    reviewMode.value = false;
}

function enterReviewMode() {
    reviewMode.value = true;
}

// ─── Virtualizer (chunked into rows of N columns) ───────────────
const rowHeight = computed(() => 56); // line height — slightly taller than the original 52 for paper feel

const virtualRowCount = computed(() => Math.ceil(props.totalCount / columns.value));

const virtualizer = useWindowVirtualizer(
    computed(() => ({
        count: virtualRowCount.value,
        estimateSize: () => rowHeight.value,
        overscan: 12,
    })),
);

const totalSize = computed(() => virtualizer.value.getTotalSize());
const virtualRows = computed(() => virtualizer.value.getVirtualItems());

const loadedStart = computed(() => props.windowStart);

function itemAt(globalIndex: number): WordListItem | undefined {
    const idx = globalIndex - loadedStart.value;
    if (idx < 0 || idx >= props.items.length) return undefined;
    return props.items[idx];
}

function getItemForCell(rowIndex: number, columnIndex: number): WordListItem | undefined {
    const globalIndex = rowIndex * columns.value + columnIndex;
    return itemAt(globalIndex);
}

// ─── Scroll triggers ─────────────────────────────────────────────
watch(
    () => {
        const rows = virtualizer.value.getVirtualItems();
        if (rows.length === 0) return null;
        const firstGlobal = rows[0].index * columns.value;
        const lastGlobal = (rows[rows.length - 1].index + 1) * columns.value - 1;
        return { first: firstGlobal, last: lastGlobal };
    },
    (range) => {
        if (!range) return;
        const loadedEnd = loadedStart.value + props.items.length;
        if (range.last >= loadedEnd - (columns.value * 4) && props.hasMore && !props.isLoading) {
            emit('load-more');
        }
        if (loadedStart.value > 0 && range.first < loadedStart.value) {
            emit('load-before', range.first);
        }
    },
);

defineExpose({
    selectedWords,
    reviewMode,
    selectAll,
    clearSelection,
    enterReviewMode,
});
</script>

<style scoped>
/* Paper aesthetic — subtle warm tone, line-ruled rows.
   Texture overlay applied via inline class for consistency with glass-ui. */
.wordlist-paper {
    /* Subtle warm tint reminiscent of aged notebook paper */
    background-image: var(--paper-clean-texture);
    background-repeat: repeat;
    background-size: var(--paper-texture-size);
    background-blend-mode: multiply;
}

/* Lined-paper effect — soft top border on each row, drawn shorter than full width */
.wordlist-paper__row {
    /* Reset — lines drawn via .wordlist-paper__line below */
}

.wordlist-paper__line {
    position: relative;
}

.wordlist-paper__line::before {
    content: '';
    position: absolute;
    top: 0;
    left: 1.25rem;
    right: 1.25rem;
    height: 1px;
    background: linear-gradient(
        to right,
        transparent 0%,
        color-mix(in srgb, var(--border) 50%, transparent) 8%,
        color-mix(in srgb, var(--border) 50%, transparent) 92%,
        transparent 100%
    );
    pointer-events: none;
}
</style>
