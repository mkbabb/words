import axios, { type AxiosResponse } from 'axios';
import type {
  LookupResponse,
  SearchResponse,
  SearchResult,
  DefinitionResponse,
  Example,
  AIResponse,
  DictionaryProvider,
  Language,
} from '@/types/api';
import type {
  SynthesizedDictionaryEntry,
  TransformedDefinition,
  ThesaurusEntry,
  VocabularySuggestionsResponse,
  SimpleExample,
} from '@/types';

// API versioning configuration
const API_VERSION = 'v1';
const API_BASE_URL = `/api/${API_VERSION}`;

const api = axios.create({
  baseURL: API_BASE_URL,
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

  // Transform flat examples array to grouped structure
  transformDefinitionExamples(definition: DefinitionResponse): TransformedDefinition {
    if (!definition.examples || !Array.isArray(definition.examples)) {
      return {
        ...definition,
        definition: definition.text, // Add alias for compatibility
        examples: {
          generated: [],
          literature: []
        }
      } as TransformedDefinition;
    }

    // Group examples by type
    const grouped = {
      generated: [] as SimpleExample[],
      literature: [] as SimpleExample[]
    };

    definition.examples.forEach((example: Example) => {
      if (example.type === 'generated') {
        grouped.generated.push({
          sentence: example.text,
          regenerable: true
        });
      } else if (example.type === 'literature') {
        grouped.literature.push({
          sentence: example.text,
          regenerable: false,
          source: example.source?.title || 'Unknown source'
        });
      }
    });

    return {
      ...definition,
      definition: definition.text, // Add alias for compatibility
      examples: grouped
    } as TransformedDefinition;
  },

  // Get word definition
  async getDefinition(
    word: string, 
    forceRefresh: boolean = false,
    providers?: DictionaryProvider[],
    languages?: Language[]
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
    
    const response = await api.get<LookupResponse>(`/lookup/${word}`, {
      params: Object.fromEntries(params.entries())
    });
    
    // Transform the response to match frontend expectations
    const transformedDefinitions = response.data.definitions?.map((def: DefinitionResponse) => 
      this.transformDefinitionExamples(def)
    ) || [];
    
    // Add frontend-specific fields
    return {
      ...response.data,
      definitions: transformedDefinitions,
      lookup_count: 0,
      regeneration_count: 0,
      status: 'active'
    } as SynthesizedDictionaryEntry;
  },

  // Get word definition with streaming progress
  async getDefinitionStream(
    word: string,
    forceRefresh: boolean = false,
    providers?: DictionaryProvider[],
    languages?: Language[],
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
      const url = `${API_BASE_URL}/lookup/${word}/stream${params.toString() ? '?' + params.toString() : ''}`;
      
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
          
          // Transform definitions if present
          const transformedDefinitions = result.definitions?.map((def: DefinitionResponse) => 
            this.transformDefinitionExamples(def)
          ) || [];
          
          // Add frontend-specific fields
          const synthesizedEntry: SynthesizedDictionaryEntry = {
            ...result,
            definitions: transformedDefinitions,
            lookup_count: 0,
            regeneration_count: 0,
            status: 'active'
          };
          
          resolve(synthesizedEntry);
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
    // Use the new AI synthesis endpoint instead of deprecated synonyms endpoint
    try {
      // First, get the word definition to provide context
      const lookupResponse = await api.get(`/lookup/${word}`);
      if (!lookupResponse.data || !lookupResponse.data.definitions || lookupResponse.data.definitions.length === 0) {
        throw new Error('No definitions found for word');
      }

      // Use the first definition for context
      const firstDefinition = lookupResponse.data.definitions[0];
      
      // Call the new AI synthesis endpoint
      const response = await api.post<AIResponse<{ synonyms: Array<{ word: string; score: number }>, confidence: number }>>('/ai/synthesize/synonyms', {
        word: word,
        definition: firstDefinition.text || firstDefinition.definition,
        part_of_speech: firstDefinition.part_of_speech,
        existing_synonyms: firstDefinition.synonyms || [],
        count: 10
      });

      // Transform the response to match ThesaurusEntry format
      return {
        word: word,
        synonyms: response.data.result.synonyms || [],
        confidence: response.data.result.confidence || 0
      };
    } catch (error) {
      console.error('Error fetching synonyms:', error);
      // Fallback to empty thesaurus entry
      return {
        word: word,
        synonyms: [],
        confidence: 0
      };
    }
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
