import { computed, reactive } from 'vue';
import { useStores } from '@/stores';

// Local UI state that doesn't need to be shared between components
const uiState = reactive({
    // Visual feedback
    isContainerHovered: false,
    
    // Modal state
    showExpandModal: false,
    
    // Scroll state
    scrollProgress: 0,
    documentHeight: 0,
    externalShrinkPercentage: 0,
    
    // Dimensions
    searchBarHeight: 64,
    expandButtonVisible: false,
    
    // Dev mode
    isDevelopment: import.meta.env.DEV
});

export function useSearchBarUI() {
    const { searchBar } = useStores();
    
    // Icon opacity based on store state and local UI state
    const iconOpacity = computed(() => {
        // Always full opacity when focused or hovered
        if (searchBar.isSearchBarFocused || uiState.isContainerHovered) {
            return 1;
        }

        // Don't fade when either dropdown is showing
        if (searchBar.showSearchControls || searchBar.showSearchResults) {
            return 1;
        }

        // Fade based on scroll progress
        const progress = uiState.scrollProgress;
        const fadeStart = 0.4;
        const fadeEnd = 0.85;

        if (progress <= fadeStart) {
            return 1;
        } else if (progress >= fadeEnd) {
            return 0.1;
        } else {
            const fadeProgress = (progress - fadeStart) / (fadeEnd - fadeStart);
            const easedProgress = 1 - Math.pow(1 - fadeProgress, 3);
            return 1 - easedProgress * 0.9;
        }
    });
    
    return {
        uiState,
        iconOpacity
    };
}