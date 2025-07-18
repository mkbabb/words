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

export interface FourierSeriesResult {
  coefficients: string[];
  approximated_values: string[];
  n_coeffs: number;
  mse: number;
}

export interface BasisData {
  index: number;
  coefficient: string;
  magnitude?: number;
  phase?: number;
  frequency?: number;
  degree?: number;
  x: number[];
  values: string[];
}

export interface UnifiedSeriesResult {
  coefficients: string[];
  approximated_values: string[];
  n_coeffs: number;
  method: string;
  type: string | null;
  basis_data: BasisData[];
  mse: number;
}

// Helper function to convert complex object to string
export const complexToString = (c: { real: number; imag: number }): string => {
  if (c.imag === 0) return c.real.toString();
  if (c.real === 0)
    return c.imag === 1 ? 'j' : c.imag === -1 ? '-j' : `${c.imag}j`;
  const imagPart =
    c.imag === 1
      ? '+j'
      : c.imag === -1
        ? '-j'
        : c.imag > 0
          ? `+${c.imag}j`
          : `${c.imag}j`;
  return `${c.real}${imagPart}`;
};

// Helper function to parse complex string to object
export const parseComplex = (s: string): { real: number; imag: number } => {
  if (s === 'j') return { real: 0, imag: 1 };
  if (s === '-j') return { real: 0, imag: -1 };

  // Handle pure real numbers
  if (!s.includes('j')) return { real: parseFloat(s), imag: 0 };

  // Handle pure imaginary numbers
  if (s.startsWith('j')) return { real: 0, imag: 1 };
  if (s === '-j') return { real: 0, imag: -1 };
  if (s.endsWith('j') && !s.includes('+') && !s.includes('-', 1)) {
    const imagStr = s.slice(0, -1);
    return { real: 0, imag: parseFloat(imagStr || '1') };
  }

  // Handle complex numbers like "1+2j" or "1-2j"
  const match = s.match(/^([+-]?\d*\.?\d*)\s*([+-])\s*(\d*\.?\d*)j$/);
  if (match) {
    const real = parseFloat(match[1] || '0');
    const imagSign = match[2] === '+' ? 1 : -1;
    const imagMag = parseFloat(match[3] || '1');
    return { real, imag: imagSign * imagMag };
  }

  // Fallback: try native complex parsing
  try {
    const complex = new Function('return ' + s.replace('j', '*1j'))();
    return { real: complex.real || 0, imag: complex.imag || 0 };
  } catch {
    return { real: 0, imag: 0 };
  }
};

export const legendreApi = {
  async getPolynomialData(
    maxDegree: number
  ): Promise<{ polynomials: LegendrePolynomial[] }> {
    const response = await api.get(`/legendre/polynomials/${maxDegree}`);
    return response.data;
  },

  async computeSeries(
    samples: number[],
    nHarmonics: number
  ): Promise<LegendreSeriesResult> {
    const response = await api.post('/legendre/series', {
      samples,
      n_harmonics: nHarmonics,
    });
    return response.data;
  },

  async processImage(
    file: File,
    encoding: string,
    nHarmonics: number,
    visualization: string
  ): Promise<any> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('encoding_method', encoding);
    formData.append('n_harmonics', nHarmonics.toString());
    formData.append('visualization_method', visualization);

    const response = await api.post('/legendre/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },
};

export const fourierApi = {
  async computeSeries(
    samples: Array<{ real: number; imag: number }>,
    nCoeffs: number
  ): Promise<FourierSeriesResult> {
    const sampleStrings = samples.map(complexToString);
    const response = await api.post('/fourier/series', {
      samples: sampleStrings,
      n_coeffs: nCoeffs,
    });
    return response.data;
  },
};

export const seriesApi = {
  async computeUnified(
    samples: Array<{ real: number; imag: number }>,
    nCoeffs: number,
    method: 'fourier' | 'legendre',
    type: 'fft' | 'quadrature' = 'fft'
  ): Promise<UnifiedSeriesResult> {
    const sampleStrings = samples.map(complexToString);
    const response = await api.post('/series/unified', {
      samples: sampleStrings,
      n_coeffs: nCoeffs,
      method,
      type,
    });
    return response.data;
  },
};

// New clean visualization API
export interface FourierTerm {
  index: number;
  coefficient: string;
  magnitude: number;
  phase: number;
  frequency: number;
}

export interface LegendreTerm {
  index: number;
  coefficient: string;
  degree: number;
  x_values: number[];
  y_values: string[];
}

export interface VisualizationResult {
  method: string;
  n_terms: number;
  original_samples: string[];
  approximation: string[];
  mse: number;
  fourier_terms: FourierTerm[];
  legendre_terms: LegendreTerm[];
  animation_domain: [number, number];
  recommended_duration: number;
}

export const visualizationApi = {
  async computeVisualization(
    samples: Array<{ real: number; imag: number }>,
    method: 'fourier' | 'legendre',
    nTerms: number,
    resolution: number = 200
  ): Promise<VisualizationResult> {
    const sampleStrings = samples.map(complexToString);
    const response = await api.post('/visualization/series', {
      samples: sampleStrings,
      method,
      n_terms: nTerms,
      resolution,
    });
    return response.data;
  },
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

  // Health check
  async healthCheck(): Promise<{ status: string }> {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
