import { ref, toValue, type MaybeRefOrGetter, type Ref } from 'vue';

export interface UseWordListSelectionOptions {
    /** All items (not just rendered). Used for select-all and range operations. */
    items: MaybeRefOrGetter<{ word: string }[]>;
}

export interface WordListSelection {
    selected: Ref<Set<string>>;
    lastClickedIndex: Ref<number>;

    /** Toggle a single item. Handles shift/ctrl modifiers. */
    toggle(word: string, index: number, event?: MouseEvent | KeyboardEvent): void;
    /** Select a contiguous range of items by index. */
    selectRange(fromIndex: number, toIndex: number): void;
    /** Select all items in the current list. */
    selectAll(): void;
    /** Clear the entire selection. */
    clearSelection(): void;
    /** Check if a word is selected. */
    isSelected(word: string): boolean;

    // Drag-select
    onPointerDown(index: number, event: PointerEvent): void;
    onPointerMove(index: number): void;
    onPointerUp(): void;
}

/**
 * Rich multi-select composable for word lists.
 *
 * Supports: click, shift+click (range), ctrl/cmd+click (toggle),
 * and pointer-drag range selection.
 */
export function useWordListSelection(
    options: UseWordListSelectionOptions,
): WordListSelection {
    const selected = ref<Set<string>>(new Set());
    const lastClickedIndex = ref(-1);

    // Drag state
    let isDragging = false;
    let dragStartIndex = -1;
    let dragAddMode = true; // true = adding to selection, false = removing

    function getItems() {
        return toValue(options.items);
    }

    function toggle(word: string, index: number, event?: MouseEvent | KeyboardEvent) {
        if (event?.shiftKey && lastClickedIndex.value >= 0) {
            // Shift+click: range select from last clicked
            selectRange(lastClickedIndex.value, index);
        } else if (event?.metaKey || event?.ctrlKey) {
            // Ctrl/Cmd+click: toggle without clearing
            const next = new Set(selected.value);
            if (next.has(word)) {
                next.delete(word);
            } else {
                next.add(word);
            }
            selected.value = next;
        } else {
            // Plain click: toggle single, clear others
            if (selected.value.has(word) && selected.value.size === 1) {
                selected.value = new Set();
            } else {
                selected.value = new Set([word]);
            }
        }

        lastClickedIndex.value = index;
    }

    function selectRange(fromIndex: number, toIndex: number) {
        const items = getItems();
        const start = Math.min(fromIndex, toIndex);
        const end = Math.max(fromIndex, toIndex);
        const next = new Set(selected.value);

        for (let i = start; i <= end && i < items.length; i++) {
            next.add(items[i].word);
        }

        selected.value = next;
    }

    function selectAll() {
        const items = getItems();
        selected.value = new Set(items.map((i) => i.word));
    }

    function clearSelection() {
        selected.value = new Set();
    }

    function isSelected(word: string): boolean {
        return selected.value.has(word);
    }

    // --- Drag select ---

    function onPointerDown(index: number, event: PointerEvent) {
        // Only left button
        if (event.button !== 0) return;
        // Don't start drag on modifier keys (those use click handlers)
        if (event.shiftKey || event.metaKey || event.ctrlKey) return;

        isDragging = true;
        dragStartIndex = index;

        const items = getItems();
        const word = items[index]?.word;
        if (!word) return;

        // If the item is already selected, drag will deselect
        dragAddMode = !selected.value.has(word);
    }

    function onPointerMove(index: number) {
        if (!isDragging || dragStartIndex < 0) return;

        const items = getItems();
        const start = Math.min(dragStartIndex, index);
        const end = Math.max(dragStartIndex, index);
        const next = new Set(selected.value);

        for (let i = start; i <= end && i < items.length; i++) {
            const word = items[i].word;
            if (dragAddMode) {
                next.add(word);
            } else {
                next.delete(word);
            }
        }

        selected.value = next;
    }

    function onPointerUp() {
        isDragging = false;
        dragStartIndex = -1;
    }

    return {
        selected,
        lastClickedIndex,
        toggle,
        selectRange,
        selectAll,
        clearSelection,
        isSelected,
        onPointerDown,
        onPointerMove,
        onPointerUp,
    };
}
