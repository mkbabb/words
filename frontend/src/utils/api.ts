import axios, { type AxiosResponse } from 'axios';
import type {
  SynthesizedDictionaryEntry,
  SearchResult,
  ThesaurusEntry,
} from '@/types';

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 60000, // 60 seconds (1 minute)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`, config.params);
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log(`API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message
    });
    return Promise.reject(error);
  }
);

export const dictionaryApi = {
  // Search for words
  async searchWord(query: string): Promise<SearchResult[]> {
    const response = await api.get(`/search`, {
      params: { q: query },
    });
    return response.data.results || [];
  },

  // Get word definition
  async getDefinition(word: string): Promise<SynthesizedDictionaryEntry> {
    const response = await api.get(`/lookup/${word}`);
    return response.data;
  },

  // Get synonyms/thesaurus data
  async getSynonyms(word: string): Promise<ThesaurusEntry> {
    const response = await api.get(`/synonyms/${word}`);
    return response.data;
  },

  // Get search suggestions
  async getSuggestions(prefix: string): Promise<string[]> {
    const response = await api.get(`/suggestions`, {
      params: { q: prefix, limit: 10 },
    });
    return response.data.suggestions || [];
  },

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;