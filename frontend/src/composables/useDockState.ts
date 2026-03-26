import { ref, watch, nextTick, onUnmounted, provide } from "vue";
import type { Ref } from "vue";

export interface UseDockStateOptions {
    /** Delay before auto-collapse after mouse leaves (ms) */
    collapseDelay?: number;
    /** Root element ref — used for contains() checks */
    rootEl: Ref<HTMLElement | null>;
    /** When true, disables click-away collapse (for inline toolbars, not floating docks) */
    persistent?: boolean;
}

export type DockState = "collapsed" | "hover" | "pinned";

export function useDockState(options: UseDockStateOptions) {
    const { collapseDelay = 2500, rootEl, persistent = false } = options;

    const state = ref<DockState>("collapsed");
    const expanded = ref(false);
    const isPinned = ref(false);

    let collapseTimer: ReturnType<typeof setTimeout> | null = null;
    let keepOpenCount = 0;
    let removeClickAway: (() => void) | null = null;

    // Suppress events briefly after mount to avoid phantom triggers
    let ignoreEvents = true;
    setTimeout(() => {
        ignoreEvents = false;
    }, 600);

    function syncDerived() {
        expanded.value = state.value !== "collapsed";
        isPinned.value = state.value === "pinned";
    }

    function clearTimer() {
        if (collapseTimer) {
            clearTimeout(collapseTimer);
            collapseTimer = null;
        }
    }

    function scheduleCollapse() {
        if (keepOpenCount > 0) return;
        clearTimer();
        collapseTimer = setTimeout(() => {
            state.value = "collapsed";
            syncDerived();
        }, collapseDelay);
    }

    function collapse() {
        clearTimer();
        state.value = "collapsed";
        syncDerived();
    }

    function expand(force = false) {
        if (ignoreEvents && !force) return;
        clearTimer();
        state.value = "hover";
        syncDerived();
    }

    // --- Mouse handlers ---

    function onMouseEnter() {
        if (ignoreEvents) return;
        clearTimer();
        if (state.value === "collapsed") {
            state.value = "hover";
            syncDerived();
        }
        // If pinned, no-op (stays pinned)
    }

    function onMouseLeave(e?: MouseEvent) {
        // If mouse moved to a descendant, don't collapse
        if (e) {
            const root = rootEl.value;
            if (
                root &&
                e.relatedTarget instanceof Node &&
                root.contains(e.relatedTarget)
            )
                return;
        }
        if (state.value === "hover") {
            if (keepOpenCount > 0) return;
            scheduleCollapse();
        }
        // If pinned, no-op (stays pinned)
    }

    // --- Focus handlers ---

    function onFocusIn() {
        if (ignoreEvents) return;
        clearTimer();
        if (state.value === "collapsed") {
            state.value = "hover";
            syncDerived();
        }
    }

    function onFocusOut(e: FocusEvent) {
        const root = e.currentTarget as HTMLElement;
        if (e.relatedTarget && root.contains(e.relatedTarget as Node)) return;
        if (keepOpenCount > 0) return;
        if (state.value === "hover") {
            scheduleCollapse();
        }
    }

    // --- Click on collapsed layer → PINNED ---

    function onClickCollapsed() {
        clearTimer();
        state.value = "pinned";
        syncDerived();
    }

    // --- keepOpen / release (ref-counted child holds) ---

    function keepOpen() {
        keepOpenCount++;
        clearTimer();
    }

    function release() {
        keepOpenCount = Math.max(0, keepOpenCount - 1);
        if (keepOpenCount === 0 && state.value === "hover") {
            scheduleCollapse();
        }
    }

    // Provide for descendant components
    provide("dockKeepOpen", keepOpen);
    provide("dockRelease", release);
    provide("dockExpanded", expanded);

    // --- Click-away listener ---

    function onPointerDownOutside(e: PointerEvent) {
        const root = rootEl.value;
        if (!root || root.contains(e.target as Node)) return;
        if (keepOpenCount > 0) return;

        // Click outside in hover state → collapse
        // Click outside in pinned state → collapse
        collapse();
    }

    // Click-away: skip for persistent docks (inline toolbars)
    if (!persistent) {
        watch(expanded, (isExpanded) => {
            if (isExpanded) {
                nextTick(() => {
                    document.addEventListener(
                        "pointerdown",
                        onPointerDownOutside,
                        true,
                    );
                    removeClickAway = () => {
                        document.removeEventListener(
                            "pointerdown",
                            onPointerDownOutside,
                            true,
                        );
                        removeClickAway = null;
                    };
                });
            } else {
                removeClickAway?.();
            }
        });
    }

    // Cleanup
    onUnmounted(() => {
        clearTimer();
        removeClickAway?.();
    });

    return {
        state,
        expanded,
        isPinned,
        onMouseEnter,
        onMouseLeave,
        onFocusIn,
        onFocusOut,
        onClickCollapsed,
        keepOpen,
        release,
        expand,
        collapse,
    };
}
