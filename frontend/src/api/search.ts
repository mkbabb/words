import type { SearchResponse, SearchResult } from '@/types/api';
import { api } from './core';

export const searchApi = {
  // Search for words using query parameter - GET /search
  async search(query: string, options?: {
    max_results?: number;
    min_score?: number;
  }): Promise<SearchResult[]> {
    try {
      // Progressive search parameters based on query length
      const getSearchParams = (q: string) => {
        const length = q.trim().length;
        return {
          max_results: options?.max_results || (length <= 4 ? 12 : 8),
          min_score: options?.min_score || (length <= 4 ? 0.2 : length <= 6 ? 0.25 : 0.3),
        };
      };

      const params = getSearchParams(query);
      const response = await api.get<SearchResponse>(`/search`, {
        params: {
          q: query,
          ...params,
        },
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

  // Rebuild search index - POST /search/rebuild-index
  async rebuildIndex(): Promise<{ message: string; status: string }> {
    try {
      const response = await api.post<{ message: string; status: string }>('/search/rebuild-index');
      return response.data;
    } catch (error) {
      console.error('Rebuild index API error:', error);
      throw error;
    }
  },
};