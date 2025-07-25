import axios, { type AxiosResponse } from 'axios';
import type {
  SynthesizedDictionaryEntry,
  SearchResult,
  ThesaurusEntry,
  VocabularySuggestionsResponse,
} from '@/types';

const api = axios.create({
  baseURL: '/api',  // Clean API path - versioning handled by deployment
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
  // Search for words using the new search API
  async searchWord(query: string): Promise<SearchResult[]> {
    try {
      // Progressive search parameters based on query length
      const getSearchParams = (q: string) => {
        const length = q.trim().length;
        return {
          max_results: length <= 4 ? 12 : 8,
          min_score: length <= 4 ? 0.2 : length <= 6 ? 0.25 : 0.3,
        };
      };

      const params = getSearchParams(query);
      const response = await api.get(`/search`, {
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

  // Get word definition
  async getDefinition(
    word: string, 
    forceRefresh: boolean = false,
    providers?: string[],
    languages?: string[]
  ): Promise<SynthesizedDictionaryEntry> {
    const params = new URLSearchParams();
    if (forceRefresh) params.append('force_refresh', 'true');
    
    // Add providers to the query parameters
    if (providers && providers.length > 0) {
      providers.forEach(provider => params.append('providers', provider));
    }
    
    // Add languages to the query parameters
    if (languages && languages.length > 0) {
      languages.forEach(language => params.append('languages', language));
    }
    
    const response = await api.get(`/lookup/${word}`, {
      params: Object.fromEntries(params.entries())
    });
    return response.data;
  },

  // Get word definition with streaming progress
  async getDefinitionStream(
    word: string,
    forceRefresh: boolean = false,
    providers?: string[],
    languages?: string[],
    onProgress?: (stage: string, progress: number, message: string, details?: any) => void
  ): Promise<SynthesizedDictionaryEntry> {
    return new Promise((resolve, reject) => {
      const params = new URLSearchParams();
      if (forceRefresh) params.append('force_refresh', 'true');
      
      // Add providers to the query parameters
      if (providers && providers.length > 0) {
        providers.forEach(provider => params.append('providers', provider));
      }
      
      // Add languages to the query parameters
      if (languages && languages.length > 0) {
        languages.forEach(language => params.append('languages', language));
      }
      
      // Use relative URL to ensure it goes through the Vite proxy
      const url = `/api/lookup/${word}/stream${params.toString() ? '?' + params.toString() : ''}`;
      
      console.log(`Opening SSE connection to: ${url}`);
      const eventSource = new EventSource(url);
      
      let hasReceivedData = false;
      let connectionTimeout: NodeJS.Timeout;
      
      // Set a timeout for initial connection
      connectionTimeout = setTimeout(() => {
        if (!hasReceivedData) {
          console.error('SSE connection timeout - no data received within 5 seconds');
          eventSource.close();
          reject(new Error('Connection timeout. Please try again.'));
        }
      }, 5000);
      
      eventSource.addEventListener('progress', (event) => {
        try {
          const data = JSON.parse(event.data);
          hasReceivedData = true;
          clearTimeout(connectionTimeout);
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
          clearTimeout(connectionTimeout);
          eventSource.close();
          console.log('SSE connection completed successfully');
          
          // Extract the result from the details field, or fallback to direct data
          const result = data.details?.result || data;
          resolve(result);
        } catch (e) {
          clearTimeout(connectionTimeout);
          eventSource.close();
          reject(new Error('Failed to parse complete event'));
        }
      });
      
      eventSource.addEventListener('error', (event) => {
        console.error('SSE error event:', event);
        clearTimeout(connectionTimeout);
        if (event.type === 'error' && (event as any).data) {
          try {
            const data = JSON.parse((event as any).data);
            eventSource.close();
            reject(new Error(data.error || 'Stream error'));
          } catch {
            // Not a JSON error message
          }
        }
      });
      
      eventSource.onerror = (error) => {
        console.error('SSE connection error:', error);
        clearTimeout(connectionTimeout);
        eventSource.close();
        
        // If we haven't received any data, it might be a connection issue
        if (!hasReceivedData) {
          reject(new Error('Failed to establish SSE connection. Please try again.'));
        } else {
          reject(new Error('Stream connection lost'));
        }
      };
    });
  },

  // Get synonyms/thesaurus data
  async getSynonyms(word: string): Promise<ThesaurusEntry> {
    const response = await api.get(`/synonyms/${word}`);
    return response.data;
  },

  // Get search autocomplete suggestions (fallback since search endpoint removed)
  async getSearchSuggestions(_prefix: string): Promise<string[]> {
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
