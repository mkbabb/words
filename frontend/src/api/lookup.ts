import type {
    DictionaryEntryResponse,
    DictionaryProvider,
    Language,
    SourceVersionSpec,
} from '@/types/api';
import type { SynthesizedDictionaryEntry } from '@/types';
import { api, transformError, API_BASE_URL } from './core';
import { logger } from '@/utils/logger';
import {
    SSEClient,
    type SSEOptions,
    type SSEHandlers,
    type ProgressEvent,
    type ConfigEvent,
} from './sse/SSEClient';

const sseClient = new SSEClient(api);

// SSE event data envelope types
interface SSECompleteEvent {
    result?: DictionaryEntryResponse;
    [key: string]: unknown;
}

interface SSEChunkEvent {
    data: Partial<DictionaryEntryResponse>;
    [key: string]: unknown;
}

export const lookupApi = {
    // Main word lookup - GET /lookup/{word}
    async lookup(
        word: string,
        options?: {
            forceRefresh?: boolean;
            providers?: DictionaryProvider[];
            languages?: Language[];
            noAI?: boolean;
        }
    ): Promise<SynthesizedDictionaryEntry> {
        try {
            const params: Record<string, any> = {};

            if (options?.forceRefresh) params.force_refresh = true;
            if (options?.providers?.length)
                params.providers = options.providers;
            if (options?.languages?.length)
                params.languages = options.languages;
            if (options?.noAI) params.no_ai = true;

            const response = await api.get<DictionaryEntryResponse>(
                `/lookup/${encodeURIComponent(word)}`,
                {
                    params,
                }
            );

            // Transform backend response to frontend model
            return {
                ...response.data,
                lookup_count: 0,
                regeneration_count: 0,
                status: 'active',
            } as SynthesizedDictionaryEntry;
        } catch (error) {
            throw transformError(error);
        }
    },

    // Re-synthesize a word (admin only) - POST /lookup/{word}/re-synthesize
    async reSynthesize(word: string): Promise<SynthesizedDictionaryEntry> {
        try {
            const response = await api.post<DictionaryEntryResponse>(
                `/lookup/${encodeURIComponent(word)}/re-synthesize`
            );
            return {
                ...response.data,
                lookup_count: 0,
                regeneration_count: 0,
                status: 'active',
            } as SynthesizedDictionaryEntry;
        } catch (error) {
            throw transformError(error);
        }
    },

    // Re-synthesize from specific provider versions - POST /lookup/{word}/synthesize-from
    async synthesizeFrom(
        word: string,
        sources: SourceVersionSpec[],
        autoIncrement = true
    ): Promise<SynthesizedDictionaryEntry> {
        try {
            const response = await api.post<DictionaryEntryResponse>(
                `/lookup/${encodeURIComponent(word)}/synthesize-from`,
                { sources, auto_increment: autoIncrement }
            );
            return {
                ...response.data,
                lookup_count: 0,
                regeneration_count: 0,
                status: 'active',
            } as SynthesizedDictionaryEntry;
        } catch (error) {
            throw transformError(error);
        }
    },

    // Streaming word lookup - GET /lookup/{word}/stream
    async lookupStream(
        word: string,
        options?: {
            forceRefresh?: boolean;
            providers?: DictionaryProvider[];
            languages?: Language[];
            noAI?: boolean;
            onProgress?: (event: ProgressEvent) => void;
            onConfig?: (event: ConfigEvent) => void;
            onPartialResult?: (
                partialEntry: Partial<SynthesizedDictionaryEntry>
            ) => void;
            abortController?: AbortController;
        }
    ): Promise<SynthesizedDictionaryEntry> {
        const params = new URLSearchParams();
        if (options?.forceRefresh) params.append('force_refresh', 'true');
        if (options?.providers?.length) {
            for (const provider of options.providers) {
                params.append('providers', provider);
            }
        }
        if (options?.languages?.length) {
            for (const language of options.languages) {
                params.append('languages', language);
            }
        }
        if (options?.noAI) params.append('no_ai', 'true');

        const url = `${API_BASE_URL}/lookup/${encodeURIComponent(word)}/stream?${params}`;

        const sseOptions: SSEOptions = {
            timeout: 120000,
            signal: options?.abortController?.signal,
            onProgress: options?.onProgress,
            onPartialResult: options?.onPartialResult
                ? (data: unknown) =>
                      options.onPartialResult!(
                          data as Partial<SynthesizedDictionaryEntry>
                      )
                : undefined,
            onConfig: options?.onConfig,
        };

        let partialResult: Partial<SynthesizedDictionaryEntry> = {};

        const handlers: SSEHandlers<SynthesizedDictionaryEntry> = {
            onEvent: (event: string, data: unknown) => {
                if (event === 'complete') {
                    // Handle both regular and chunked completion
                    const completeEvent = data as SSECompleteEvent;
                    const result = (completeEvent.result ||
                        data) as DictionaryEntryResponse;
                    return {
                        ...result,
                        lookup_count: 0,
                        regeneration_count: 0,
                        status: 'active',
                    } as SynthesizedDictionaryEntry;
                }

                if (event === 'completion_chunk') {
                    // Handle incremental chunked data
                    const chunkData = (data as SSEChunkEvent).data;
                    partialResult = {
                        ...partialResult,
                        ...chunkData,
                        lookup_count: 0,
                        regeneration_count: 0,
                        status: 'active',
                    };

                    if (options?.onPartialResult) {
                        options.onPartialResult(partialResult);
                    }
                }

                return null;
            },
            onComplete: () => {
                // Additional processing if needed
            },
            onError: (error: Error) => {
                logger.error('Stream error:', error);
            },
        };

        return sseClient.stream(url, sseOptions, handlers);
    },
};
