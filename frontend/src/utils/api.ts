import axios, { type AxiosResponse } from '@/utils/mock-axios';
import type {
  ApiResponse,
  SynthesizedDictionaryEntry,
  SearchResult,
  ThesaurusEntry,
} from '@/types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config: any) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error: any) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => response,
  (error: any) => {
    console.error('API Error:', error.response?.data || error.message);
    return Promise.reject(error);
  }
);

export const dictionaryApi = {
  // Search for words
  async searchWord(query: string): Promise<ApiResponse<SearchResult[]>> {
    const response = await api.get(`/search/word`, {
      params: { q: query },
    });
    return response.data;
  },

  // Get word definition
  async getDefinition(word: string): Promise<ApiResponse<SynthesizedDictionaryEntry>> {
    const response = await api.get(`/lookup/${word}`);
    return response.data;
  },

  // Get synonyms/thesaurus data
  async getSynonyms(word: string): Promise<ApiResponse<ThesaurusEntry>> {
    const response = await api.get(`/synonyms/${word}`);
    return response.data;
  },

  // Get search suggestions
  async getSuggestions(prefix: string): Promise<ApiResponse<string[]>> {
    const response = await api.get(`/search/suggestions`, {
      params: { prefix, limit: 10 },
    });
    return response.data;
  },

  // Health check
  async healthCheck(): Promise<ApiResponse<{ status: string }>> {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;