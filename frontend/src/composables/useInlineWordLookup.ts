/**
 * Composable for inline word lookup via text selection.
 *
 * UX: User selects text → floating "Define" pill appears → click → mini-definition popover.
 * Desktop shortcut: double-click a word → immediate popover.
 *
 * Exposes `isActive` so parent components can maintain their hover state
 * even when the mouse moves to the teleported pill/popover.
 */
import { ref, computed, onMounted, onUnmounted, nextTick, type Ref, type ComputedRef } from 'vue';

export interface InlineWordLookupState {
    selectedWord: Ref<string>;
    isPillVisible: Ref<boolean>;
    isPopoverVisible: Ref<boolean>;
    /** True when pill or popover is showing — parents should treat this as "still hovered" */
    isActive: ComputedRef<boolean>;
    position: Ref<{ x: number; y: number }>;
    dismiss: () => void;
    showPopover: () => void;
}

/**
 * Extract a single clean word from a text selection.
 * Minimum 3 characters to avoid function words like "or", "is", "at".
 */
function extractWord(selection: Selection): string | null {
    const text = selection.toString().trim();
    if (!text) return null;

    // Only accept single words (letters, hyphens, apostrophes)
    if (!text.match(/^[\p{L}\p{M}'-]+$/u)) return null;

    // 3-char minimum skips most function words; 50-char max for sanity
    if (text.length < 3 || text.length > 50) return null;

    return text.toLowerCase();
}

function getSelectionRect(selection: Selection): DOMRect | null {
    if (selection.rangeCount === 0) return null;
    const range = selection.getRangeAt(0);
    const rect = range.getBoundingClientRect();
    if (rect.width === 0 && rect.height === 0) return null;
    return rect;
}

/** Check if an element is inside our pill or popover (teleported to body). */
function isLookupElement(el: EventTarget | null): boolean {
    if (!el || !(el instanceof HTMLElement)) return false;
    return !!(
        el.closest('[data-word-lookup-pill]') ||
        el.closest('[data-word-lookup-popover]')
    );
}

export function useInlineWordLookup(
    containerRef: Ref<HTMLElement | null>,
): InlineWordLookupState {
    const selectedWord = ref('');
    const isPillVisible = ref(false);
    const isPopoverVisible = ref(false);
    const position = ref({ x: 0, y: 0 });

    // Parents can watch this to maintain hover state while pill/popover is open
    const isActive = computed(() => isPillVisible.value || isPopoverVisible.value);

    let dismissTimeout: ReturnType<typeof setTimeout> | null = null;

    function dismiss() {
        isPillVisible.value = false;
        isPopoverVisible.value = false;
        selectedWord.value = '';
    }

    function showPopover() {
        if (!selectedWord.value) return;
        isPillVisible.value = false;
        isPopoverVisible.value = true;
    }

    function handleSelectionChange() {
        if (isPopoverVisible.value) return;

        const selection = window.getSelection();
        if (!selection || selection.isCollapsed) {
            if (dismissTimeout) clearTimeout(dismissTimeout);
            dismissTimeout = setTimeout(() => {
                if (!isPopoverVisible.value) {
                    isPillVisible.value = false;
                }
            }, 200);
            return;
        }

        const container = containerRef.value;
        if (!container) return;

        const anchorNode = selection.anchorNode;
        if (!anchorNode || !container.contains(anchorNode)) return;

        const word = extractWord(selection);
        if (!word) {
            isPillVisible.value = false;
            return;
        }

        const rect = getSelectionRect(selection);
        if (!rect) return;

        selectedWord.value = word;
        position.value = {
            x: rect.left + rect.width / 2,
            y: rect.top,
        };
        isPillVisible.value = true;
    }

    function handleDblClick(e: MouseEvent) {
        const container = containerRef.value;
        if (!container) return;
        if (!container.contains(e.target as Node)) return;

        nextTick(() => {
            const selection = window.getSelection();
            if (!selection) return;

            const word = extractWord(selection);
            if (!word) return;

            const rect = getSelectionRect(selection);
            if (!rect) return;

            selectedWord.value = word;
            position.value = {
                x: rect.left + rect.width / 2,
                y: rect.top,
            };
            isPillVisible.value = false;
            isPopoverVisible.value = true;
        });
    }

    function handleClickOutside(e: MouseEvent) {
        // Don't dismiss when interacting with pill/popover
        if (isLookupElement(e.target)) return;
        dismiss();
    }

    onMounted(() => {
        document.addEventListener('selectionchange', handleSelectionChange);
        document.addEventListener('dblclick', handleDblClick);
        document.addEventListener('mousedown', handleClickOutside);
    });

    onUnmounted(() => {
        document.removeEventListener('selectionchange', handleSelectionChange);
        document.removeEventListener('dblclick', handleDblClick);
        document.removeEventListener('mousedown', handleClickOutside);
        if (dismissTimeout) clearTimeout(dismissTimeout);
    });

    return {
        selectedWord,
        isPillVisible,
        isPopoverVisible,
        isActive,
        position,
        dismiss,
        showPopover,
    };
}
