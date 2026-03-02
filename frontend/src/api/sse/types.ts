/**
 * SSE (Server-Sent Events) Type Definitions
 *
 * Interfaces for SSE event handling, progress tracking,
 * chunked completions, and stream configuration.
 */

// Backend-aligned SSE event types
export interface ProgressEvent {
    stage: string; // Backend detailed stage names
    progress: number; // 0-100
    message?: string; // Human-readable status
    details?: Record<string, unknown>; // Stage-specific details
    is_complete?: boolean; // Pipeline completion flag
    error?: string | null; // Error message if failed
}

export interface ConfigEvent {
    category: string;
    stages: Array<{
        progress: number;
        label: string;
        description: string;
    }>;
}

export interface ChunkedCompletionStart {
    message: string;
    total_definitions?: number;
}

export interface ChunkedCompletionChunk {
    chunk_type: 'basic_info' | 'definition' | 'examples';
    definition_index?: number;
    batch_start?: number;
    data: unknown;
}

export interface CompletionEvent {
    type?: 'complete' | 'error';
    message: string;
    result?: unknown;
    chunked?: boolean;
}

export interface SSEOptions {
    timeout?: number;
    signal?: AbortSignal;
    onProgress?: (event: ProgressEvent) => void;
    onPartialResult?: (data: unknown) => void;
    onConfig?: (event: ConfigEvent) => void;
}

export interface SSEHandlers<T> {
    onEvent: (event: string, data: unknown) => T | null;
    onComplete: (result: T) => void;
    onError?: (error: Error) => void;
}
