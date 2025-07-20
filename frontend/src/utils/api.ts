import axios, { type AxiosResponse } from 'axios';
import type {
  SynthesizedDictionaryEntry,
  SearchResult,
  ThesaurusEntry,
  VocabularySuggestionsResponse,
  FactsAPIResponse,
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
  config => {
    console.log(
      `API Request: ${config.method?.toUpperCase()} ${config.url}`,
      config.params
    );
    return config;
  },
  error => Promise.reject(error)
);

// Response interceptor
api.interceptors.response.use(
  (response: AxiosResponse) => {
    console.log(
      `API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`,
      response.data
    );
    return response;
  },
  error => {
    console.error('API Error:', {
      url: error.config?.url,
      method: error.config?.method,
      status: error.response?.status,
      statusText: error.response?.statusText,
      data: error.response?.data,
      message: error.message,
    });
    return Promise.reject(error);
  }
);


export const dictionaryApi = {
  // Search for words (fallback to lookup-based search since dedicated search endpoint removed)
  async searchWord(query: string): Promise<SearchResult[]> {
    // Since standalone search endpoints were removed, return empty results
    // Frontend can use other suggestion mechanisms instead
    console.warn('Search endpoint removed - using lookup-based workflow instead');
    return [];
  },

  // Get word definition
  async getDefinition(word: string, forceRefresh: boolean = false): Promise<SynthesizedDictionaryEntry> {
    const response = await api.get(`/lookup/${word}`, {
      params: forceRefresh ? { force_refresh: true } : undefined
    });
    return response.data;
  },

  // Get word definition with streaming progress
  async getDefinitionStream(
    word: string,
    forceRefresh: boolean = false,
    onProgress?: (stage: string, progress: number, message: string, details?: any) => void
  ): Promise<SynthesizedDictionaryEntry> {
    return new Promise((resolve, reject) => {
      const params = new URLSearchParams();
      if (forceRefresh) params.append('force_refresh', 'true');
      
      const url = `/api/v1/lookup/${word}/stream${params.toString() ? '?' + params.toString() : ''}`;
      const eventSource = new EventSource(url);
      
      eventSource.addEventListener('progress', (event) => {
        try {
          const data = JSON.parse(event.data);
          if (onProgress) {
            onProgress(data.stage, data.progress, data.message, data.details);
          }
        } catch (e) {
          console.error('Error parsing progress event:', e);
        }
      });
      
      eventSource.addEventListener('complete', (event) => {
        try {
          const data = JSON.parse(event.data);
          eventSource.close();
          resolve(data);
        } catch (e) {
          eventSource.close();
          reject(new Error('Failed to parse complete event'));
        }
      });
      
      eventSource.addEventListener('error', (event) => {
        eventSource.close();
        if (event.type === 'error') {
          try {
            const data = JSON.parse((event as any).data);
            reject(new Error(data.error || 'Stream error'));
          } catch {
            reject(new Error('Connection error'));
          }
        }
      });
      
      eventSource.onerror = () => {
        eventSource.close();
        reject(new Error('Stream connection failed'));
      };
    });
  },

  // Get synonyms/thesaurus data
  async getSynonyms(word: string): Promise<ThesaurusEntry> {
    const response = await api.get(`/synonyms/${word}`);
    return response.data;
  },

  // Get search autocomplete suggestions (fallback since search endpoint removed)
  async getSearchSuggestions(prefix: string): Promise<string[]> {
    // Since standalone search endpoints were removed, return empty suggestions
    // Frontend can use vocabulary suggestions or other mechanisms instead
    console.warn('Search suggestions endpoint removed - using vocabulary suggestions instead');
    return [];
  },

  // Get vocabulary suggestions based on lookup history
  async getVocabularySuggestions(
    words: string[]
  ): Promise<VocabularySuggestionsResponse> {
    // Use GET when no words (empty array), POST when words provided
    if (!words || words.length === 0) {
      const response = await api.get(`/suggestions`, {
        params: { count: 10 },
      });
      return response.data;
    } else {
      const response = await api.post(`/suggestions`, {
        words: words.slice(0, 10), // Take last 10 words max
        count: 10,
      });
      return response.data;
    }
  },

  // Get interesting facts about a word
  async getWordFacts(
    word: string,
    count: number = 5,
    previousWords?: string[]
  ): Promise<FactsAPIResponse> {
    const params: any = { count };
    if (previousWords && previousWords.length > 0) {
      params.previous_words = previousWords.slice(0, 20); // Limit to 20 words
    }
    
    const response = await api.get(`/facts/${word}`, { params });
    return response.data;
  },

  // Regenerate examples for a definition
  async regenerateExamples(
    word: string,
    definitionIndex: number,
    definitionText?: string,
    count?: number
  ): Promise<{
    word: string;
    definition_index: number;
    examples: Array<{ sentence: string; regenerable: boolean }>;
    confidence: number;
  }> {
    const response = await api.post(`/lookup/${word}/regenerate-examples`, {
      definition_index: definitionIndex,
      definition_text: definitionText,
      count: count || 2,
    });
    return response.data;
  },

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
