import type { SearchResponse, SearchResult } from '@/types/api';
import { api } from './core';

export const searchApi = {
  // Search for words using query parameter - GET /search
  async search(query: string, options?: {
    max_results?: number;
    min_score?: number;
    semantic?: boolean;
    semantic_weight?: number;
    signal?: AbortSignal;
  }): Promise<SearchResult[]> {
    try {
      // Progressive search parameters based on query length
      const getSearchParams = (q: string) => {
        const length = q.trim().length;
        return {
          max_results: options?.max_results || (length <= 4 ? 12 : 8),
          min_score: options?.min_score || (length <= 4 ? 0.2 : length <= 6 ? 0.25 : 0.3),
          semantic: options?.semantic || false,
          semantic_weight: options?.semantic_weight || 0.7,
        };
      };

      const params = getSearchParams(query);
      const response = await api.get<SearchResponse>(`/search`, {
        params: {
          q: query,
          ...params,
        },
        signal: options?.signal,
      });
      return response.data.results || [];
    } catch (error) {
      console.error('Search API error:', error);
      return [];
    }
  },

  // Search for words using path parameter - GET /search/{query}
  async searchByPath(query: string, options?: {
    max_results?: number;
    min_score?: number;
  }): Promise<SearchResult[]> {
    try {
      const params = {
        max_results: options?.max_results || 10,
        min_score: options?.min_score || 0.3,
      };
      
      const response = await api.get<SearchResponse>(`/search/${encodeURIComponent(query)}`, {
        params
      });
      return response.data.results || [];
    } catch (error) {
      console.error('Search by path API error:', error);
      return [];
    }
  },

  // Get search suggestions - GET /search/{query}/suggestions
  async getSuggestions(query: string, options?: {
    max_results?: number;
  }): Promise<string[]> {
    try {
      const params = {
        max_results: options?.max_results || 10,
      };
      
      const response = await api.get<{ suggestions: string[] }>(`/search/${encodeURIComponent(query)}/suggestions`, {
        params
      });
      return response.data.suggestions || [];
    } catch (error) {
      console.error('Search suggestions API error:', error);
      return [];
    }
  },

  // Rebuild search index with unified corpus management - POST /search/rebuild-index
  async rebuildIndex(options?: {
    languages?: string[];
    corpus_types?: string[];
    rebuild_all_corpora?: boolean;
    rebuild_semantic?: boolean;
    semantic_force_rebuild?: boolean;
    quantization_type?: string;
    auto_semantic_small_corpora?: boolean;
    clear_existing_cache?: boolean;
    force_download?: boolean;
  }): Promise<{
    status: string;
    languages: string[];
    message: string;
    total_time_seconds: number;
    corpus_results: Record<string, any>;
    corpus_manager_stats: Record<string, any>;
  }> {
    try {
      const requestData = {
        languages: options?.languages || ['en'],
        corpus_types: options?.corpus_types || ['language_search'],
        rebuild_all_corpora: options?.rebuild_all_corpora || false,
        rebuild_semantic: options?.rebuild_semantic ?? true,
        semantic_force_rebuild: options?.semantic_force_rebuild || false,
        quantization_type: options?.quantization_type || 'binary',
        auto_semantic_small_corpora: options?.auto_semantic_small_corpora ?? true,
        clear_existing_cache: options?.clear_existing_cache || false,
        force_download: options?.force_download ?? true,
      };
      
      const response = await api.post('/search/rebuild-index', requestData);
      return response.data;
    } catch (error) {
      console.error('Rebuild index API error:', error);
      throw error;
    }
  },

  // Invalidate corpus caches - POST /search/invalidate-corpus
  async invalidateCorpus(options?: {
    corpus_types?: string[];
    specific_corpus_id?: string;
    invalidate_all?: boolean;
    cleanup_expired?: boolean;
  }): Promise<{
    status: string;
    total_invalidated: number;
    corpus_results: Record<string, number>;
    expired_cleaned: number;
    message: string;
  }> {
    try {
      const requestData = {
        corpus_types: options?.corpus_types || [],
        specific_corpus_id: options?.specific_corpus_id,
        invalidate_all: options?.invalidate_all || false,
        cleanup_expired: options?.cleanup_expired ?? true,
      };
      
      const response = await api.post('/search/invalidate-corpus', requestData);
      return response.data;
    } catch (error) {
      console.error('Invalidate corpus API error:', error);
      throw error;
    }
  },
};