import axios, { type AxiosResponse } from 'axios';
import type {
  SynthesizedDictionaryEntry,
  SearchResult,
  ThesaurusEntry,
  VocabularySuggestionsResponse,
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

export interface LegendrePolynomial {
  degree: number;
  x: number[];
  y: number[];
}

export interface LegendreSeriesResult {
  coefficients: number[];
  approximated_values: number[];
  n_harmonics: number;
  mse: number;
}

export const legendreApi = {
  async getPolynomialData(maxDegree: number): Promise<{ polynomials: LegendrePolynomial[] }> {
    const response = await api.get(`/legendre/polynomials/${maxDegree}`);
    return response.data;
  },

  async computeSeries(samples: number[], nHarmonics: number): Promise<LegendreSeriesResult> {
    const response = await api.post('/legendre/series', {
      samples,
      n_harmonics: nHarmonics
    });
    return response.data;
  },

  async processImage(file: File, encoding: string, nHarmonics: number, visualization: string): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('encoding_method', encoding);
    formData.append('n_harmonics', nHarmonics.toString());
    formData.append('visualization_method', visualization);

    const response = await api.post('/legendre/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
    return response.data;
  }
};

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

  // Get search autocomplete suggestions (for search bar)
  async getSearchSuggestions(prefix: string): Promise<string[]> {
    const response = await api.get(`/search`, {
      params: { q: prefix, limit: 10 },
    });
    return response.data.results?.map((r: SearchResult) => r.word) || [];
  },

  // Get vocabulary suggestions based on lookup history
  async getVocabularySuggestions(words: string[]): Promise<VocabularySuggestionsResponse> {
    // Use GET when no words (empty array), POST when words provided
    if (!words || words.length === 0) {
      const response = await api.get(`/suggestions`, {
        params: { count: 10 }
      });
      return response.data;
    } else {
      const response = await api.post(`/suggestions`, {
        words: words.slice(0, 10), // Take last 10 words max
        count: 10
      });
      return response.data;
    }
  },

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;