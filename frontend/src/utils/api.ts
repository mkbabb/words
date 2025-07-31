import axios, { type AxiosResponse } from 'axios';
import type {
  DictionaryEntryResponse,
  SearchResponse,
  SearchResult,
  AIResponse,
  DictionaryProvider,
  Language,
  ImageMedia,
  ResourceResponse,
  HealthResponse,
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

// Create axios instance with standardized configuration
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000, // 60 seconds (1 minute)
  headers: {
    'Content-Type': 'application/json',
  },
});

// Error type for consistent error handling
export interface APIError {
  message: string;
  code?: string;
  field?: string;
  details?: any;
}

// Transform error responses to consistent format
function transformError(error: any): APIError {
  if (error.response?.data?.error) {
    return {
      message: error.response.data.error,
      details: error.response.data.details,
    };
  }
  return {
    message: error.message || 'An unknown error occurred',
    code: error.code,
  };
}

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


  // Get word definition with standardized parameters
  async getDefinition(
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

  // Get word definition with streaming progress
  async getDefinitionStream(
    word: string,
    forceRefresh: boolean = false,
    providers?: DictionaryProvider[],
    languages?: Language[],
    onProgress?: (stage: string, progress: number, message: string, details?: any) => void,
    onConfig?: (category: string, stages: Array<{progress: number, label: string, description: string}>) => void,
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
      
      // Handle config events for dynamic stage setup
      eventSource.addEventListener('config', (event) => {
        try {
          const data = JSON.parse(event.data);
          hasReceivedData = true;
          clearTimeout(connectionTimeout);
          if (onConfig) {
            onConfig(data.category, data.stages);
          }
        } catch (e) {
          console.error('Error parsing config event:', e);
        }
      });
      
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
          
          // Extract the result from the new structured format
          const result = data.result || data.details?.result || data;
          
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
            reject(new Error(data.error || data.message || 'Stream error'));
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

  // Get synonyms using AI synthesis endpoint
  async getSynonyms(word: string): Promise<ThesaurusEntry> {
    try {
      // Get word context from lookup
      const lookupResponse = await api.get<DictionaryEntryResponse>(`/lookup/${encodeURIComponent(word)}`);
      
      if (!lookupResponse.data?.definitions?.length) {
        throw new Error('No definitions found for word');
      }

      const firstDefinition = lookupResponse.data.definitions[0];
      
      // Call AI synthesis endpoint with consistent parameter structure
      const response = await api.post<AIResponse<{ 
        synonyms: Array<{ word: string; score: number }>;
        confidence: number;
      }>>('/ai/synthesize/synonyms', {
        word,
        definition: firstDefinition.text,
        part_of_speech: firstDefinition.part_of_speech,
        existing_synonyms: firstDefinition.synonyms || [],
        count: 10
      });

      // Transform response to frontend format
      return {
        word,
        synonyms: response.data.result.synonyms || [],
        confidence: response.data.result.confidence || 0
      };
    } catch (error) {
      console.error('Error fetching synonyms:', error);
      throw transformError(error);
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
    onProgress?: (stage: string, progress: number, message?: string, details?: any) => void,
    onConfig?: (category: string, stages: Array<{progress: number, label: string, description: string}>) => void
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

      // Handle config events for dynamic stage setup
      eventSource.addEventListener('config', (event) => {
        const data = JSON.parse(event.data);
        if (onConfig) {
          onConfig(data.category, data.stages);
        }
      });
      
      // Handle progress events
      eventSource.addEventListener('progress', (event) => {
        const data = JSON.parse(event.data);
        if (onProgress) {
          onProgress(data.stage, data.progress, data.message, data.details);
        }
      });

      // Handle completion
      eventSource.addEventListener('complete', (event) => {
        const data = JSON.parse(event.data);
        eventSource.close();
        // Extract result from new structured format
        const result = data.result || data;
        resolve(result as WordSuggestionResponse);
      });

      // Handle errors
      eventSource.addEventListener('error', (event: any) => {
        if (event.data) {
          const data = JSON.parse(event.data);
          eventSource.close();
          reject(new Error(data.error || data.message || 'Unknown error'));
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

  // Health check with proper response type
  async healthCheck(): Promise<HealthResponse> {
    try {
      const response = await api.get<HealthResponse>('/health');
      return response.data;
    } catch (error) {
      throw transformError(error);
    }
  },

  // Update definition with ResourceResponse wrapper
  async updateDefinition(definitionId: string, updates: Partial<{
    text: string;
    part_of_speech: string;
    synonyms: string[];
    antonyms: string[];
    language_register: string;
    domain: string;
    region: string;
    cefr_level: string;
    frequency_band: number;
  }>): Promise<ResourceResponse> {
    console.log('[API] Updating definition:', definitionId, 'with:', updates);
    try {
      const response = await api.put<ResourceResponse>(`/definitions/${definitionId}`, updates);
      console.log('[API] Update successful:', response.data);
      return response.data;
    } catch (error) {
      console.error('[API] Update failed:', error);
      throw transformError(error);
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

export const imageApi = {
  // Upload image
  async uploadImage(file: File, options?: {
    alt_text?: string;
    description?: string;
  }): Promise<ImageMedia> {
    const formData = new FormData();
    formData.append('file', file);
    
    const params = new URLSearchParams();
    if (options?.alt_text) params.append('alt_text', options.alt_text);
    if (options?.description) params.append('description', options.description);
    
    const response = await api.post<ResourceResponse>(
      `/images${params.toString() ? '?' + params.toString() : ''}`,
      formData
    );
    
    // Extract image data from ResourceResponse
    return {
      id: response.data.data.id,
      url: response.data.data.url,
      format: response.data.data.format,
      size_bytes: response.data.data.size_bytes,
      width: response.data.data.width,
      height: response.data.data.height,
      alt_text: response.data.data.alt_text,
      description: response.data.data.description,
      created_at: response.data.data.created_at,
      updated_at: response.data.data.updated_at,
      version: response.data.data.version || 1,
    };
  },

  // Get image metadata
  async getImage(imageId: string): Promise<ImageMedia> {
    const response = await api.get(`/images/${imageId}`);
    return response.data;
  },

  // Update image metadata
  async updateImage(imageId: string, updates: {
    alt_text?: string;
    description?: string;
  }): Promise<ImageMedia> {
    const response = await api.put<ResourceResponse>(`/images/${imageId}`, updates);
    return response.data.data;
  },

  // Delete image
  async deleteImage(imageId: string): Promise<void> {
    await api.delete(`/images/${imageId}`);
  },

  // Bind image to definition
  async bindImageToDefinition(definitionId: string, imageId: string): Promise<any> {
    const response = await api.patch(`/definitions/${definitionId}`, {
      add_image_id: imageId
    });
    return response.data;
  },

  // Remove image from definition
  async removeImageFromDefinition(definitionId: string, imageId: string): Promise<any> {
    const response = await api.patch(`/definitions/${definitionId}`, {
      remove_image_id: imageId
    });
    return response.data;
  }
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

  // Upload wordlist file with streaming progress
  async uploadWordlistStream(
    file: File,
    options?: {
      name?: string;
      description?: string;
      is_public?: boolean;
    },
    onProgress?: (stage: string, progress: number, message?: string, details?: any) => void,
    onConfig?: (category: string, stages: Array<{progress: number, label: string, description: string}>) => void
  ): Promise<{
    id: string;
    name: string;
    word_count: number;
    created_at: string;
    metadata: any;
    links: any;
  }> {
    return new Promise((resolve, reject) => {
      const formData = new FormData();
      formData.append('file', file);
      
      if (options?.name) formData.append('name', options.name);
      if (options?.description) formData.append('description', options.description);
      if (options?.is_public !== undefined) formData.append('is_public', options.is_public.toString());

      // Create FormData URL params for the streaming endpoint
      const params = new URLSearchParams();
      if (options?.name) params.append('name', options.name);
      if (options?.description) params.append('description', options.description);
      if (options?.is_public !== undefined) params.append('is_public', options.is_public.toString());

      // Use XMLHttpRequest for file upload with SSE-like response handling
      const xhr = new XMLHttpRequest();
      
      xhr.open('POST', `${API_BASE_URL}/wordlists/upload/stream${params.toString() ? '?' + params.toString() : ''}`, true);
      
      let buffer = '';
      let hasReceivedData = false;
      
      xhr.onreadystatechange = () => {
        if (xhr.readyState === 3 || xhr.readyState === 4) { // LOADING or DONE
          hasReceivedData = true;
          
          // Get new data
          const newData = xhr.responseText.substr(buffer.length);
          buffer = xhr.responseText;
          
          // Parse SSE events from new data
          const lines = newData.split('\n');
          let eventData = '';
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              eventData = line.substr(6);
              try {
                const data = JSON.parse(eventData);
                
                if (data.type === 'config' && onConfig) {
                  onConfig(data.category, data.stages);
                } else if (data.type === 'progress' && onProgress) {
                  onProgress(data.stage, data.progress, data.message, data.details);
                } else if (data.type === 'complete') {
                  resolve(data.result);
                  return;
                } else if (data.type === 'error') {
                  reject(new Error(data.message));
                  return;
                }
              } catch (e) {
                console.error('Error parsing SSE data:', e);
              }
            }
          }
        }
      };
      
      xhr.onerror = () => {
        reject(new Error('Upload failed'));
      };
      
      xhr.ontimeout = () => {
        reject(new Error('Upload timeout'));
      };
      
      xhr.timeout = 60000; // 60 second timeout
      xhr.send(formData);
      
      // Fallback timeout for no initial response
      setTimeout(() => {
        if (!hasReceivedData) {
          xhr.abort();
          reject(new Error('No response from server'));
        }
      }, 5000);
    });
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
    sort_by?: string;
    sort_order?: 'asc' | 'desc';
    mastery_level?: string;
    min_views?: number;
    max_views?: number;
    reviewed?: boolean;
  }) {
    const params: Record<string, any> = {
      offset: options?.offset || 0,
      limit: options?.limit || 50,
    };
    
    // Add optional parameters
    if (options?.sort_by) params.sort_by = options.sort_by;
    if (options?.sort_order) params.sort_order = options.sort_order;
    if (options?.mastery_level) params.mastery_level = options.mastery_level;
    if (options?.min_views !== undefined) params.min_views = options.min_views;
    if (options?.max_views !== undefined) params.max_views = options.max_views;
    if (options?.reviewed !== undefined) params.reviewed = options.reviewed;
    
    const response = await api.get(`/wordlists/${id}/words`, { params });
    return response.data;
  },

  // Get wordlist statistics
  async getStatistics(id: string) {
    const response = await api.get(`/wordlists/${id}/statistics`);
    return response.data;
  },

  // Submit word review
  async submitWordReview(wordlistId: string, review: {
    word: string;
    quality: number; // 0-5 for SM-2 algorithm
  }) {
    const response = await api.post(`/wordlists/${wordlistId}/review`, review);
    return response.data;
  },

  // Get due words for review
  async getDueWords(wordlistId: string, limit: number = 20) {
    const response = await api.get(`/wordlists/${wordlistId}/review/due`, {
      params: { limit }
    });
    return response.data;
  },

  // Update word in wordlist (notes, tags, etc)
  async updateWord(wordlistId: string, wordText: string, updates: {
    notes?: string;
    tags?: string[];
  }) {
    // Since backend doesn't have a direct update endpoint, we'll need to handle this differently
    // For now, return a mock response
    console.warn('updateWord API not implemented on backend');
    return { data: { ...updates, word: wordText } };
  },
};

export default api;
