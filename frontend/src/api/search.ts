import type { SearchResponse, SearchResult, SemanticStatusResponse } from '@/types/api';
import { api } from './core';
import { logger } from '@/utils/logger';

export const searchApi = {
  // Search for words using query parameter - GET /search
  // Defaults are owned by the backend (SearchParams in models/parameters.py).
  // Only send parameters the caller explicitly provides — omitted params use
  // backend defaults (mode=smart, min_score=0.3, max_results=20).
  async search(query: string, options?: {
    max_results?: number;
    min_score?: number;
    mode?: string;
    languages?: string[];
    corpus_name?: string;
    signal?: AbortSignal;
  }): Promise<SearchResult[]> {
    try {
      const params: Record<string, unknown> = { q: query };
      if (options?.max_results != null) params.max_results = options.max_results;
      if (options?.min_score != null) params.min_score = options.min_score;
      if (options?.mode != null) params.mode = options.mode;
      if (options?.languages) params.languages = options.languages;
      if (options?.corpus_name) params.corpus_name = options.corpus_name;

      const response = await api.get<SearchResponse>(`/search`, {
        params,
        signal: options?.signal,
      });
      return response.data.results || [];
    } catch (error: any) {
      // Rethrow cancel errors so callers can handle them without overwriting fresh results
      if (error.name === 'AbortError' || error.name === 'CanceledError' || error.code === 'ERR_CANCELED') {
        throw error;
      }
      // Silently drop 429 rate limit responses — debounce handles the retry
      if (error.response?.status === 429) {
        return [];
      }
      logger.error('Search API error:', error);
      return [];
    }
  },

  // Search for words using path parameter - GET /search/{query}
  async searchByPath(query: string, options?: {
    max_results?: number;
    min_score?: number;
  }): Promise<SearchResult[]> {
    try {
      const params: Record<string, unknown> = {};
      if (options?.max_results != null) params.max_results = options.max_results;
      if (options?.min_score != null) params.min_score = options.min_score;

      const response = await api.get<SearchResponse>(`/search/${encodeURIComponent(query)}`, {
        params
      });
      return response.data.results || [];
    } catch (error) {
      logger.error('Search by path API error:', error);
      return [];
    }
  },

  // Get search suggestions - GET /search/{query}/suggestions
  async getSuggestions(query: string, options?: {
    max_results?: number;
  }): Promise<string[]> {
    try {
      const params: Record<string, unknown> = {};
      if (options?.max_results != null) params.max_results = options.max_results;

      const response = await api.get<{ suggestions: string[] }>(`/search/${encodeURIComponent(query)}/suggestions`, {
        params
      });
      return response.data.suggestions || [];
    } catch (error) {
      logger.error('Search suggestions API error:', error);
      return [];
    }
  },

  // Get semantic search status - GET /search/semantic/status
  async getSemanticStatus(): Promise<SemanticStatusResponse> {
    const { data } = await api.get<SemanticStatusResponse>('/search/semantic/status');
    return data;
  },

  // Rebuild search index - POST /search/rebuild
  // Isomorphic to backend RebuildIndexRequest (search/models.py)
  async rebuildIndex(options?: {
    corpus_name?: string;
    corpus_uuid?: string;
    languages?: string[];
    components?: string[];
    clear_caches?: boolean;
    clean_gridfs?: boolean;
  }): Promise<{
    status: string;
    message: string;
    corpus_name: string;
    corpus_uuid?: string;
    components_rebuilt: string[];
    vocabulary_size: number;
    caches_cleared: Record<string, number>;
    gridfs_cleaned: number;
    total_time_seconds: number;
    semantic_info: Record<string, any>;
  }> {
    try {
      const body: Record<string, unknown> = {};
      if (options?.corpus_name != null) body.corpus_name = options.corpus_name;
      if (options?.corpus_uuid != null) body.corpus_uuid = options.corpus_uuid;
      if (options?.languages != null) body.languages = options.languages;
      if (options?.components != null) body.components = options.components;
      if (options?.clear_caches != null) body.clear_caches = options.clear_caches;
      if (options?.clean_gridfs != null) body.clean_gridfs = options.clean_gridfs;

      const response = await api.post('/search/rebuild', body);
      return response.data;
    } catch (error) {
      logger.error('Rebuild index API error:', error);
      throw error;
    }
  },

  // Invalidate corpus caches - POST /corpus/invalidate
  async invalidateCorpus(options?: {
    specific_corpus_id?: string;
    invalidate_all?: boolean;
  }): Promise<{
    status: string;
    total_invalidated: number;
    message: string;
  }> {
    try {
      const requestData = {
        specific_corpus_id: options?.specific_corpus_id,
        invalidate_all: options?.invalidate_all || false,
      };
      
      const response = await api.post('/corpus/invalidate', requestData);
      return response.data;
    } catch (error) {
      logger.error('Invalidate corpus API error:', error);
      throw error;
    }
  },
};
