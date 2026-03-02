import { watch, onUnmounted, type WatchStopHandle } from 'vue';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { shouldTriggerAIMode } from '@/components/custom/search/utils/ai-query';

/**
 * Composable that watches the search query and detects AI mode.
 *
 * Extracted from lookup store to follow "no side-effects in stores" principle.
 * The store retains setAIQuery() and setShowSparkle() state setters;
 * this composable manages the reactive watcher lifecycle.
 */
export function useAIQueryDetection() {
    const searchBar = useSearchBarStore();
    const lookupMode = useLookupMode();

    let queryWatchStopHandle: WatchStopHandle | null = null;

    const start = () => {
        stop();
        queryWatchStopHandle = watch(
            () => searchBar.searchQuery || '',
            (newQuery) => {
                if (newQuery && newQuery.length > 0) {
                    const shouldBeAI = shouldTriggerAIMode(newQuery);
                    if (shouldBeAI !== lookupMode.isAIQuery) {
                        lookupMode.setAIQuery(shouldBeAI);
                        if (shouldBeAI) {
                            lookupMode.setShowSparkle(true);
                        }
                    }
                } else {
                    // Reset AI mode for empty queries
                    if (lookupMode.isAIQuery) {
                        lookupMode.setAIQuery(false);
                        lookupMode.setShowSparkle(false);
                    }
                }
            }
        );
    };

    const stop = () => {
        if (queryWatchStopHandle) {
            queryWatchStopHandle();
            queryWatchStopHandle = null;
        }
    };

    // Auto-cleanup when the component unmounts
    onUnmounted(() => {
        stop();
    });

    return { start, stop };
}
