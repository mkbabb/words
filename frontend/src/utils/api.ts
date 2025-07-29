import axios, { type AxiosResponse } from 'axios';
import type {
  LookupResponse,
  SearchResponse,
  SearchResult,
  AIResponse,
  DictionaryProvider,
  Language,
} from '@/types/api';
import type {
  SynthesizedDictionaryEntry,
  ThesaurusEntry,
  VocabularySuggestionsResponse,
  WordSuggestionResponse,
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


  // Get word definition
  async getDefinition(
    word: string, 
    forceRefresh: boolean = false,
    providers?: DictionaryProvider[],
    languages?: Language[],
    noAI?: boolean
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
    
    // Add noAI parameter
    if (noAI) {
      params.append('no_ai', 'true');
    }
    
    const response = await api.get<LookupResponse>(`/lookup/${word}`, {
      params: Object.fromEntries(params.entries())
    });
    
    // Add frontend-specific fields (no transformation needed)
    return {
      ...response.data,
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
    onProgress?: (stage: string, progress: number, message: string, details?: any) => void,
    noAI?: boolean
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
      
      // Add noAI parameter
      if (noAI) {
        params.append('no_ai', 'true');
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
          
          // Add frontend-specific fields (no transformation needed)
          const synthesizedEntry: SynthesizedDictionaryEntry = {
            ...result,
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

  // Get AI word suggestions from descriptive query
  async getAISuggestions(query: string, count: number = 12): Promise<WordSuggestionResponse> {
    // Cap count at 25 (backend limit)
    const cappedCount = Math.min(Math.max(count, 1), 25);
    const response = await api.post('/ai/suggest-words', {
      query,
      count: cappedCount
    });
    return response.data;
  },

  // Get AI word suggestions with streaming progress
  async getAISuggestionsStream(
    query: string,
    count: number = 12,
    onProgress?: (stage: string, progress: number, message?: string) => void
  ): Promise<WordSuggestionResponse> {
    return new Promise((resolve, reject) => {
      // Cap count at 25 (backend limit)
      const cappedCount = Math.min(Math.max(count, 1), 25);
      const params = new URLSearchParams({
        query: query,
        count: cappedCount.toString()
      });
      
      const eventSource = new EventSource(
        `${API_BASE_URL}/ai/suggest-words/stream?${params.toString()}`
      );

      // Handle progress events
      eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        if (onProgress) {
          onProgress(data.stage, data.progress, data.message);
        }
      });

      // Handle completion
      eventSource.addEventListener('complete', (event) => {
        const data = JSON.parse(event.data);
        eventSource.close();
        resolve(data as WordSuggestionResponse);
      });

      // Handle errors
      eventSource.addEventListener('error', (event: any) => {
        if (event.data) {
          const data = JSON.parse(event.data);
          eventSource.close();
          reject(new Error(data.error || 'Unknown error'));
        } else {
          eventSource.close();
          reject(new Error('Connection error'));
        }
      });

      // Connection timeout
      setTimeout(() => {
        if (eventSource.readyState === EventSource.CONNECTING) {
          eventSource.close();
          reject(new Error('Connection timeout'));
        }
      }, 5000);
    });
  },

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await api.get('/health');
    return response.data;
  },

  // Update definition
  async updateDefinition(definitionId: string, updates: any): Promise<any> {
    console.log('[API] Updating definition:', definitionId, 'with:', updates);
    try {
      const response = await api.put(`/definitions/${definitionId}`, updates);
      console.log('[API] Update successful:', response.data);
      return response.data;
    } catch (error) {
      console.error('[API] Update failed:', error);
      throw error;
    }
  },

  // Update example
  async updateExample(exampleId: string, updates: { text: string }): Promise<any> {
    console.log('[API] Updating example:', exampleId, 'with:', updates);
    try {
      const response = await api.put(`/examples/${exampleId}`, updates);
      console.log('[API] Example update successful:', response.data);
      return response.data;
    } catch (error) {
      console.error('[API] Example update failed:', error);
      throw error;
    }
  },

  // Regenerate definition component
  async regenerateDefinitionComponent(definitionId: string, component: string): Promise<any> {
    const response = await api.post(`/definitions/${definitionId}/regenerate`, {
      components: [component],
      force: true
    });
    return response.data.data;
  },

  // Get definition by ID
  async getDefinitionById(definitionId: string): Promise<any> {
    const response = await api.get(`/definitions/${definitionId}`);
    return response.data.data;
  },
};

export const wordlistApi = {
  // Get all wordlists
  async getWordlists(params?: {
    offset?: number;
    limit?: number;
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    owner_id?: string;
  }) {
    const response = await api.get('/wordlists', { params });
    return response.data;
  },

  // Get single wordlist by ID
  async getWordlist(id: string) {
    const response = await api.get(`/wordlists/${id}`);
    return response.data;
  },

  // Create new wordlist
  async createWordlist(data: {
    name: string;
    description?: string;
    words?: string[];
    tags?: string[];
    is_public?: boolean;
    owner_id?: string;
  }) {
    const response = await api.post('/wordlists', data);
    return response.data;
  },

  // Upload wordlist file
  async uploadWordlist(file: File, options?: {
    name?: string;
    description?: string;
    tags?: string;
    is_public?: boolean;
    owner_id?: string;
  }) {
    const formData = new FormData();
    formData.append('file', file);
    
    if (options?.name) formData.append('name', options.name);
    if (options?.description) formData.append('description', options.description);
    if (options?.tags) formData.append('tags', options.tags);
    if (options?.is_public !== undefined) formData.append('is_public', options.is_public.toString());
    if (options?.owner_id) formData.append('owner_id', options.owner_id);

    const response = await api.post('/wordlists/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // Update wordlist
  async updateWordlist(id: string, data: {
    name?: string;
    description?: string;
    tags?: string[];
    is_public?: boolean;
  }) {
    const response = await api.put(`/wordlists/${id}`, data);
    return response.data;
  },

  // Delete wordlist
  async deleteWordlist(id: string) {
    await api.delete(`/wordlists/${id}`);
  },

  // Add words to wordlist
  async addWords(id: string, words: string[]) {
    const response = await api.post(`/wordlists/${id}/words`, { words });
    return response.data;
  },

  // Remove word from wordlist
  async removeWord(id: string, word: string) {
    await api.delete(`/wordlists/${id}/words/${encodeURIComponent(word)}`);
  },

  // Search within wordlist
  async searchWordlist(id: string, query: string, options?: {
    max_results?: number;
    min_score?: number;
  }) {
    const params = {
      query,
      max_results: options?.max_results || 20,
      min_score: options?.min_score || 0.6,
    };
    const response = await api.post(`/wordlists/${id}/search`, null, { params });
    return response.data;
  },

  // Get wordlist words (paginated)
  async getWordlistWords(id: string, options?: {
    offset?: number;
    limit?: number;
    sort?: Array<{field: string, direction: 'asc' | 'desc'}>;
    filters?: Record<string, any>;
    search?: string;
  }) {
    const criteria = {
      filters: options?.filters || {},
      sort: options?.sort || [],
      search: options?.search || ""
    };
    
    const params = {
      criteria: JSON.stringify(criteria),
      offset: options?.offset || 0,
      limit: options?.limit || 50,
    };
    
    const response = await api.get(`/wordlists/${id}/words`, { params });
    return response.data;
  },

  // Get wordlist statistics
  async getStatistics(id: string) {
    const response = await api.get(`/wordlists/${id}/statistics`);
    return response.data;
  },
};

export default api;
