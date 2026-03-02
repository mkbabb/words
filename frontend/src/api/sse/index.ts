/**
 * SSE Module - Barrel Export
 *
 * Re-exports SSE client and all SSE types.
 */

export { SSEClient } from './SSEClient';
export type {
    ProgressEvent,
    ConfigEvent,
    ChunkedCompletionStart,
    ChunkedCompletionChunk,
    CompletionEvent,
    SSEOptions,
    SSEHandlers,
} from './types';
