import { computed, watch, ref, onMounted, onUnmounted } from 'vue';
import { useSearchBarUI } from './useSearchBarUI';
import { useStores } from '@/stores';

interface UseSearchBarScrollOptions {
    shrinkPercentage: () => number;
}

/**
 * Unified composable for SearchBar scroll animations and effects
 * Handles scroll progress, container styling, and responsive behavior
 */
export function useSearchBarScroll(options: UseSearchBarScrollOptions) {
    const { searchBar } = useStores();
    const { uiState } = useSearchBarUI();
    const { shrinkPercentage } = options;

    // Track viewport width for responsive behavior
    const viewportWidth = ref(
        typeof window !== 'undefined' ? window.innerWidth : 1024
    );

    const updateViewportWidth = () => {
        viewportWidth.value = window.innerWidth;
    };

    onMounted(() => {
        window.addEventListener('resize', updateViewportWidth);
        updateViewportWidth();
    });

    onUnmounted(() => {
        window.removeEventListener('resize', updateViewportWidth);
    });

    // Hysteresis: debounce the interactive state to prevent rapid bouncing
    // at the scroll threshold boundary when focus/blur triggers layout shifts.
    const isInteractive = ref(false);
    let interactiveTimer: ReturnType<typeof setTimeout> | null = null;

    watch(
        () =>
            searchBar.isFocused ||
            uiState.isContainerHovered ||
            searchBar.showSearchControls ||
            searchBar.showDropdown,
        (active) => {
            if (interactiveTimer) clearTimeout(interactiveTimer);
            if (active) {
                // Expand immediately
                isInteractive.value = true;
            } else {
                // Shrink with a short delay to prevent bounce
                interactiveTimer = setTimeout(() => {
                    isInteractive.value = false;
                }, 150);
            }
        },
        { immediate: true }
    );

    // Container style — uses only transform + opacity (no layout-affecting
    // properties like maxWidth) so the sticky search bar never causes reflow
    // feedback loops when content height changes during scroll.
    const containerStyle = computed(() => {
        const progress = uiState.scrollProgress;
        const isMobile = viewportWidth.value < 640;

        // Constant maxWidth — never changes during scroll to avoid layout shifts
        const maxWidth = isMobile
            ? 'calc(100vw - 0.5rem)'
            : 'min(32rem, calc(100vw - 2rem))';

        // Interactive states: always full size
        if (isInteractive.value) {
            return {
                maxWidth,
                transform: 'scale(1)',
                opacity: '1',
                transition: `transform var(--duration-normal, 0.3s) var(--ease-decelerate, cubic-bezier(0.25, 0.46, 0.45, 0.94)), opacity var(--duration-normal, 0.3s) var(--ease-decelerate, cubic-bezier(0.25, 0.46, 0.45, 0.94))`,
            };
        }

        // Unfocused: apply visual-only shrink via transform (no layout reflow)
        const baselineShrink = 0.35;
        const effectiveProgress = Math.max(baselineShrink, Math.min(progress, 1));

        const scale = isMobile ? 1 : 1 - effectiveProgress * 0.15;
        const opacity = Math.max(0.65, 0.85 - effectiveProgress * 0.2);

        return {
            maxWidth,
            transform: `scale(${scale})`,
            opacity: opacity.toString(),
            transition: `transform var(--duration-fast, 0.2s) var(--ease-decelerate, cubic-bezier(0.25, 0.46, 0.45, 0.94)), opacity var(--duration-fast, 0.2s) var(--ease-decelerate, cubic-bezier(0.25, 0.46, 0.45, 0.94))`,
        };
    });

    // Update scroll progress from external prop
    watch(
        shrinkPercentage,
        (newValue) => {
            uiState.scrollProgress = newValue;
        },
        { immediate: true }
    );

    return {
        // Computed
        containerStyle,
    };
}
