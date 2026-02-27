import type {
  DictionaryEntryResponse,
  DictionaryProvider,
  Language,
} from '@/types/api';
import type { SynthesizedDictionaryEntry } from '@/types';
import { api, transformError, API_BASE_URL } from './core';
import { logger } from '@/utils/logger';
import { 
  SSEClient, 
  type SSEOptions, 
  type SSEHandlers,
  type ProgressEvent,
  type ConfigEvent 
} from './sse/SSEClient';

const sseClient = new SSEClient(api);

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
      if (options?.providers?.length) params.providers = options.providers;
      if (options?.languages?.length) params.languages = options.languages;
      if (options?.noAI) params.no_ai = true;
      
      const response = await api.get<DictionaryEntryResponse>(`/lookup/${encodeURIComponent(word)}`, {
        params
      });
      
      // Transform backend response to frontend model
      return {
        ...response.data,
        lookup_count: 0,
        regeneration_count: 0,
        status: 'active'
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
      onPartialResult?: (partialEntry: Partial<SynthesizedDictionaryEntry>) => void;
      abortController?: AbortController;
    }
  ): Promise<SynthesizedDictionaryEntry> {
    const params = new URLSearchParams();
    if (options?.forceRefresh) params.append('force_refresh', 'true');
    if (options?.providers?.length) params.append('providers', options.providers.join(','));
    if (options?.languages?.length) params.append('languages', options.languages.join(','));
    if (options?.noAI) params.append('no_ai', 'true');

    const url = `${API_BASE_URL}/lookup/${encodeURIComponent(word)}/stream?${params}`;

    const sseOptions: SSEOptions = {
      timeout: 120000,
      signal: options?.abortController?.signal,
      onProgress: options?.onProgress,
      onPartialResult: options?.onPartialResult ? (data: unknown) => options.onPartialResult!(data as Partial<SynthesizedDictionaryEntry>) : undefined,
      onConfig: options?.onConfig
    };

    let partialResult: Partial<SynthesizedDictionaryEntry> = {};

    const handlers: SSEHandlers<SynthesizedDictionaryEntry> = {
      onEvent: (event: string, data: unknown) => {
        if (event === 'complete') {
          // Handle both regular and chunked completion
          const result = (data as any).result || data;
          return {
            ...result,
            lookup_count: 0,
            regeneration_count: 0,
            status: 'active'
          } as SynthesizedDictionaryEntry;
        }

        if (event === 'completion_chunk') {
          // Handle incremental chunked data
          const chunkData = (data as any).data;
          partialResult = {
            ...partialResult,
            ...chunkData,
            lookup_count: 0,
            regeneration_count: 0,
            status: 'active'
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
      }
    };

    return sseClient.stream(url, sseOptions, handlers);
  }
};