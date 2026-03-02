import { onUnmounted } from 'vue';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { searchApi } from '@/api';
import { logger } from '@/utils/logger';

/**
 * Composable that polls the semantic search status endpoint.
 *
 * Extracted from lookup store to follow "no API calls in stores" principle.
 * The store retains the semanticStatus ref (state); this composable manages
 * the polling lifecycle and writes status updates into the store.
 */
export function useSemanticStatusPoller() {
    const lookupMode = useLookupMode();

    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
        try {
            const status = await searchApi.getSemanticStatus();
            lookupMode.setSemanticStatus(status);

            // Stop polling when search engine is ready or semantic is disabled
            if (status.ready || !status.enabled) {
                stop();
            }
        } catch (e) {
            logger.debug('Semantic status poll failed:', e);
        }
    };

    const start = () => {
        stop();
        // Initial fetch
        poll();
        // Poll every 5s
        pollTimer = setInterval(poll, 5000);
    };

    const stop = () => {
        if (pollTimer) {
            clearInterval(pollTimer);
            pollTimer = null;
        }
    };

    // Auto-cleanup when the component unmounts
    onUnmounted(() => {
        stop();
    });

    return { start, stop };
}
