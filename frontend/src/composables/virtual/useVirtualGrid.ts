import { computed, watch, toValue, type MaybeRefOrGetter } from 'vue';
import { useWindowVirtualizer } from '@tanstack/vue-virtual';
import type { WordListItem } from '@/types';

export interface UseVirtualGridOptions<T = WordListItem> {
    /** Loaded items (the current window of data). */
    items: MaybeRefOrGetter<T[]>;
    /** Total item count from backend (for accurate scrollbar height). */
    totalCount: MaybeRefOrGetter<number>;
    /** Logical offset of items[0] in the full list (for windowed eviction). */
    windowStart?: MaybeRefOrGetter<number>;
    /** Number of columns in the grid (reactive). */
    columnCount: MaybeRefOrGetter<number>;
    /** Estimated row height in pixels. Default: 100. */
    rowHeight?: number;
    /** Rows of overscan above/below viewport. Default: 3. */
    overscan?: number;
    /** Rows from end of loaded data to trigger onLoadMore. Default: 5. */
    loadThreshold?: number;
    /** Called when the user scrolls near the end of loaded data. */
    onLoadMore?: () => void;
    /** Called when the user scrolls backward into evicted data. Receives the first visible item offset. */
    onLoadBefore?: (firstVisibleOffset: number) => void;
}

export function useVirtualGrid<T = WordListItem>(options: UseVirtualGridOptions<T>) {
    const rowHeight = options.rowHeight ?? 100;
    const overscan = options.overscan ?? 3;
    const loadThreshold = options.loadThreshold ?? 5;

    const items = computed(() => toValue(options.items));
    const totalCount = computed(() => toValue(options.totalCount));
    const windowStartVal = computed(() => toValue(options.windowStart) ?? 0);
    const cols = computed(() => Math.max(1, toValue(options.columnCount)));

    // Chunk items into rows based on column count
    const rows = computed(() => {
        const c = cols.value;
        const src = items.value;
        const result: T[][] = [];
        for (let i = 0; i < src.length; i += c) {
            result.push(src.slice(i, i + c));
        }
        return result;
    });

    // Total row count uses backend total (for accurate scrollbar)
    const totalRowCount = computed(() => {
        const t = totalCount.value;
        if (t > 0) return Math.ceil(t / cols.value);
        return rows.value.length;
    });

    // Row offset where loaded data starts
    const loadedRowStart = computed(() =>
        Math.floor(windowStartVal.value / cols.value),
    );

    const virtualizer = useWindowVirtualizer(
        computed(() => ({
            count: totalRowCount.value,
            estimateSize: () => rowHeight,
            overscan,
        })),
    );

    // Map virtual row index → loaded data row (undefined if outside window)
    function getRowData(virtualRowIndex: number): T[] | undefined {
        const dataRowIndex = virtualRowIndex - loadedRowStart.value;
        if (dataRowIndex < 0 || dataRowIndex >= rows.value.length) return undefined;
        return rows.value[dataRowIndex];
    }

    // Watch visible items for both forward and backward scroll triggers
    watch(
        () => {
            const vItems = virtualizer.value.getVirtualItems();
            if (vItems.length === 0) return null;
            return {
                first: vItems[0]?.index ?? 0,
                last: vItems[vItems.length - 1]?.index ?? 0,
            };
        },
        (range) => {
            if (!range) return;

            // Forward: load more when near end of loaded data
            if (options.onLoadMore) {
                const loadedEnd = loadedRowStart.value + rows.value.length;
                if (range.last >= loadedEnd - loadThreshold) {
                    options.onLoadMore();
                }
            }

            // Backward: re-fetch when scrolling into evicted zone
            if (options.onLoadBefore && loadedRowStart.value > 0) {
                if (range.first < loadedRowStart.value) {
                    const firstVisibleOffset = range.first * cols.value;
                    options.onLoadBefore(firstVisibleOffset);
                }
            }
        },
    );

    return {
        virtualizer,
        rows,
        totalRowCount,
        loadedRowStart,
        totalSize: computed(() => virtualizer.value.getTotalSize()),
        virtualItems: computed(() => virtualizer.value.getVirtualItems()),
        getRowData,
        columnCount: cols,
    };
}
