<template>
    <!-- Loading skeleton -->
    <Card v-if="isLoading && items.length === 0" class="overflow-hidden p-0">
        <div v-for="i in 10" :key="i" :class="['flex items-center gap-4 px-4 py-3', i > 1 && 'border-t border-border/15']">
            <div class="flex-1 space-y-1.5">
                <div class="h-4 w-32 rounded bg-muted animate-pulse" />
                <div class="h-3 w-20 rounded bg-muted/50 animate-pulse" />
            </div>
            <div class="h-3 w-10 rounded-full bg-muted/40 animate-pulse" />
        </div>
    </Card>

    <!-- Word list inside a Card -->
    <Card v-else class="overflow-hidden p-0">
        <div :style="{ height: `${totalSize}px`, position: 'relative', width: '100%' }">
            <div
                v-for="vItem in virtualItems"
                :key="vItem.index"
                :style="{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    transform: `translateY(${vItem.start}px)`,
                }"
            >
                <template v-if="itemAt(vItem.index)">
                    <div :class="vItem.index > 0 && 'border-t border-border/15'">
                        <WordListRow
                            :word="itemAt(vItem.index)!"
                            :index="vItem.index"
                            :is-selected="selectedWords.has(itemAt(vItem.index)!.word)"
                            @click="(w, idx, ev) => handleRowClick(w, idx, ev)"
                        />
                    </div>
                </template>
                <!-- Skeleton for evicted/unloaded rows -->
                <div v-else :class="['flex items-center gap-4 px-4 py-3', vItem.index > 0 && 'border-t border-border/15']">
                    <div class="flex-1 space-y-1.5">
                        <div class="h-4 w-32 rounded bg-muted animate-pulse" />
                        <div class="h-3 w-20 rounded bg-muted/50 animate-pulse" />
                    </div>
                </div>
            </div>
        </div>

        <!-- Loading more -->
        <div v-if="isLoading && items.length > 0" class="flex items-center justify-center py-3 border-t border-border/15">
            <div class="h-3.5 w-3.5 animate-spin rounded-full border-b-2 border-primary" />
            <span class="ml-2 text-xs text-muted-foreground">Loading more...</span>
        </div>
    </Card>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useWindowVirtualizer } from '@tanstack/vue-virtual';
import { Card } from '@/components/ui/card';
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

// ─── Selection (managed here, exposed to parent) ─────────────────
const selectedWords = ref<Set<string>>(new Set());
const lastClickedIndex = ref(-1);
const reviewMode = ref(false);

function handleRowClick(word: WordListItem, index: number, event: MouseEvent) {
    if (reviewMode.value) {
        // In review mode: selection behavior
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
        // Normal mode: open word detail
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

// ─── Virtualizer ─────────────────────────────────────────────────
const ROW_HEIGHT = 52;
const loadedStart = computed(() => props.windowStart);

const rowCount = computed(() =>
    props.totalCount > 0 ? props.totalCount : props.items.length,
);

const virtualizer = useWindowVirtualizer(
    computed(() => ({
        count: rowCount.value,
        estimateSize: () => ROW_HEIGHT,
        overscan: 20,
    })),
);

const totalSize = computed(() => virtualizer.value.getTotalSize());
const virtualItems = computed(() => virtualizer.value.getVirtualItems());

function itemAt(virtualIndex: number): WordListItem | undefined {
    const idx = virtualIndex - loadedStart.value;
    if (idx < 0 || idx >= props.items.length) return undefined;
    return props.items[idx];
}

// ─── Scroll triggers ─────────────────────────────────────────────
watch(
    () => {
        const items = virtualizer.value.getVirtualItems();
        if (items.length === 0) return null;
        return { first: items[0].index, last: items[items.length - 1].index };
    },
    (range) => {
        if (!range) return;
        const loadedEnd = loadedStart.value + props.items.length;
        if (range.last >= loadedEnd - 10 && props.hasMore && !props.isLoading) {
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
