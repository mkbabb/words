import { api, API_BASE_URL } from './core';
import type { 
  WordListQueryParams, 
  WordListSearchQueryParams, 
  WordListsQueryParams,
  WordListNamesSearchParams 
} from '@/types/wordlist';

export const wordlistsApi = {
  // Get all wordlists
  async getWordlists(params?: WordListsQueryParams) {
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

  // Search within wordlist with full filtering and pagination
  async searchWordlist(id: string, searchParams: WordListSearchQueryParams) {
    const params: Record<string, any> = {
      query: searchParams.query,
      max_results: searchParams.max_results || 100,
      min_score: searchParams.min_score || 0.4,
      sort_by: searchParams.sort_by || 'relevance',
      sort_order: searchParams.sort_order || 'desc',
      offset: searchParams.offset || 0,
      limit: searchParams.limit || 20,
    };
    
    // Add optional filtering parameters only if they are defined
    if (searchParams.mastery_levels) params.mastery_levels = searchParams.mastery_levels;
    if (searchParams.hot_only !== undefined) params.hot_only = searchParams.hot_only;
    if (searchParams.due_only !== undefined) params.due_only = searchParams.due_only;
    if (searchParams.min_views !== undefined) params.min_views = searchParams.min_views;
    if (searchParams.max_views !== undefined) params.max_views = searchParams.max_views;
    if (searchParams.reviewed !== undefined) params.reviewed = searchParams.reviewed;
    
    const response = await api.post(`/wordlists/${id}/search`, null, { params });
    return response.data;
  },

  // Get wordlist words (paginated)
  async getWordlistWords(id: string, params?: WordListQueryParams) {
    const queryParams: Record<string, any> = {
      offset: params?.offset || 0,
      limit: params?.limit || 50,
    };
    
    // Add optional parameters
    if (params?.sort_by) queryParams.sort_by = params.sort_by;
    if (params?.sort_order) queryParams.sort_order = params.sort_order;
    if (params?.mastery_levels) queryParams.mastery_levels = params.mastery_levels;
    if (params?.hot_only !== undefined) queryParams.hot_only = params.hot_only;
    if (params?.due_only !== undefined) queryParams.due_only = params.due_only;
    if (params?.min_views !== undefined) queryParams.min_views = params.min_views;
    if (params?.max_views !== undefined) queryParams.max_views = params.max_views;
    if (params?.reviewed !== undefined) queryParams.reviewed = params.reviewed;
    
    const response = await api.get(`/wordlists/${id}/words`, { params: queryParams });
    return response.data;
  },

  // Get wordlist statistics
  async getStatistics(id: string) {
    const response = await api.get(`/wordlists/${id}/stats`);
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

  // Search wordlists by name
  async searchWordlists(query: string, params?: WordListNamesSearchParams) {
    const queryParams: Record<string, any> = {
      limit: params?.limit || 10,
    };
    
    const response = await api.get(`/wordlists/search/${encodeURIComponent(query)}`, { params: queryParams });
    return response.data;
  },

  // Generate a random slug name for wordlists
  async generateSlugName(): Promise<{ name: string }> {
    // Add cache-busting parameter to ensure fresh requests
    const response = await api.get('/wordlists/generate-name', {
      params: {
        t: Date.now()
      },
      headers: {
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
      }
    });
    return response.data;
  },

  // Update word in wordlist (notes, tags, etc)
  async updateWord(wordlistId: string, wordText: string, updates: {
    notes?: string;
    tags?: string[];
  }) {
    const response = await api.patch(
      `/wordlists/${wordlistId}/words/${encodeURIComponent(wordText)}`,
      updates
    );
    return response.data;
  },
};