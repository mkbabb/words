import { onUnmounted } from 'vue';
import { useLookupMode } from '@/stores/search/modes/lookup';
import { API_BASE_URL } from '@/api/core';
import { logger } from '@/utils/logger';
import type { SemanticStatusResponse } from '@/types/api';

/**
 * Composable that streams semantic search status via SSE.
 *
 * Replaces the previous polling approach with a server-pushed event stream.
 * The backend sends `status` events whenever the semantic state changes
 * and auto-closes the stream on terminal states (ready / disabled).
 *
 * Falls back to a one-shot GET if EventSource is unavailable.
 */
export function useSemanticStatusPoller() {
    const lookupMode = useLookupMode();

    let eventSource: EventSource | null = null;
    let retryTimeout: ReturnType<typeof setTimeout> | null = null;
    let retryCount = 0;
    const MAX_RETRIES = 5;
    const BASE_RETRY_DELAY = 2000;

    const connect = () => {
        stop();

        const url = `${API_BASE_URL}/search/semantic/status/stream`;
        eventSource = new EventSource(url);

        eventSource.addEventListener('status', (event: MessageEvent) => {
            try {
                const status: SemanticStatusResponse = JSON.parse(event.data);
                lookupMode.setSemanticStatus(status);
                // Reset retry count on successful message
                retryCount = 0;

                // Terminal states — server closes the stream, but also
                // proactively close on the client side.
                if (status.ready || !status.enabled) {
                    stop();
                }
            } catch (e) {
                logger.debug('Failed to parse semantic status event:', e);
            }
        });

        // Named 'error' SSE events from the backend (distinct from onerror)
        eventSource.addEventListener('error', ((event: Event) => {
            const msgEvent = event as MessageEvent;
            if (msgEvent.data) {
                try {
                    const data = JSON.parse(msgEvent.data);
                    logger.error('Semantic status stream error event:', data.message);
                } catch {
                    // Not a JSON error event
                }
            }
        }) as EventListener);

        eventSource.onerror = () => {
            // EventSource fires onerror on connection close (normal for
            // terminal states) and on actual errors.
            const wasOpen = eventSource?.readyState === EventSource.OPEN;
            stop();

            // Retry with backoff if we haven't exhausted retries
            if (retryCount < MAX_RETRIES && wasOpen) {
                const delay = BASE_RETRY_DELAY * Math.pow(2, retryCount);
                retryCount++;
                logger.debug(
                    `Semantic status stream lost, retry ${retryCount}/${MAX_RETRIES} in ${delay}ms`
                );
                retryTimeout = setTimeout(connect, delay);
            } else if (retryCount >= MAX_RETRIES) {
                logger.debug(
                    'Semantic status stream: max retries reached, giving up'
                );
                lookupMode.setSemanticStatus(null);
            }
            // If !wasOpen, the stream closed cleanly (terminal state) — no retry
        };
    };

    const start = () => {
        retryCount = 0;
        connect();
    };

    const stop = () => {
        if (retryTimeout) {
            clearTimeout(retryTimeout);
            retryTimeout = null;
        }
        if (eventSource) {
            eventSource.close();
            eventSource = null;
        }
    };

    onUnmounted(() => {
        stop();
    });

    return { start, stop };
}
