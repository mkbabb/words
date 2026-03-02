/**
 * AI Standalone Operations
 *
 * Query validation, word suggestions (standard + streaming),
 * full entry synthesis, and usage note generation.
 */

import type { AIResponse } from '@/types/api';
import type { WordSuggestionResponse } from '@/types';
import { api, API_BASE_URL } from '../core';
import { logger } from '@/utils/logger';
import { SSEClient, type SSEOptions, type SSEHandlers } from '../sse/SSEClient';

const sseClient = new SSEClient(api);

// Validate query - POST /ai/validate-query
export async function validateQuery(query: string): Promise<{
    valid: boolean;
    suggestions?: string[];
    issues?: string[];
}> {
    const response = await api.post<
        AIResponse<{
            valid: boolean;
            suggestions?: string[];
            issues?: string[];
        }>
    >('/ai/validate-query', { query });

    return response.data.result;
}

// Generate usage notes - POST /ai/usage-notes
export async function generateUsageNotes(
    word: string,
    definition?: string
): Promise<{
    word: string;
    notes: Array<{ category: string; note: string }>;
    confidence: number;
}> {
    const response = await api.post<
        AIResponse<{
            notes: Array<{ category: string; note: string }>;
            confidence: number;
        }>
    >('/ai/usage-notes', {
        word,
        definition,
    });

    return {
        word,
        notes: response.data.result.notes || [],
        confidence: response.data.result.confidence || 0,
    };
}

// Synthesize entire entry - POST /ai/synthesize
export async function synthesizeEntry(
    word: string,
    options?: {
        components?: string[];
        force?: boolean;
    }
): Promise<any> {
    const response = await api.post('/ai/synthesize', {
        word,
        components: options?.components || ['all'],
        force: options?.force || false,
    });
    return response.data;
}

// Word suggestions - POST /ai/suggest-words
export async function suggestWords(
    query: string,
    count: number = 12
): Promise<WordSuggestionResponse> {
    // Cap count at 25 (backend limit)
    const cappedCount = Math.min(Math.max(count, 1), 25);
    const response = await api.post('/ai/suggest-words', {
        query,
        count: cappedCount,
    });
    return response.data;
}

// Word suggestions with streaming - GET /ai/suggest-words/stream
export async function suggestWordsStream(
    query: string,
    count: number = 12,
    onProgress?: (
        stage: string,
        progress: number,
        message?: string,
        details?: any
    ) => void,
    onConfig?: (
        category: string,
        stages: Array<{
            progress: number;
            label: string;
            description: string;
        }>
    ) => void
): Promise<WordSuggestionResponse> {
    // Cap count at 25 (backend limit)
    const cappedCount = Math.min(Math.max(count, 1), 25);
    const params = new URLSearchParams({
        query: query,
        count: cappedCount.toString(),
    });

    const url = `${API_BASE_URL}/ai/suggest-words/stream?${params.toString()}`;

    const sseOptions: SSEOptions = {
        timeout: 30000, // 30 seconds for AI suggestions
        onProgress: onProgress
            ? (event) =>
                  onProgress(
                      event.stage,
                      event.progress,
                      event.message,
                      event.details
                  )
            : undefined,
        onConfig: onConfig
            ? (event) => onConfig(event.category, event.stages)
            : undefined,
    };

    const handlers: SSEHandlers<WordSuggestionResponse> = {
        onEvent: (event: string, data: any) => {
            if (event === 'completion' || event === 'complete') {
                return data.result || data;
            }
            return null;
        },
        onComplete: () => {},
        onError: (error: Error) => {
            logger.error('AI suggestions stream error:', error);
        },
    };

    return sseClient.stream(url, sseOptions, handlers);
}
