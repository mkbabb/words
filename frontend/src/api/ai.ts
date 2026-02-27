import type {
  AIResponse,
  DictionaryEntryResponse,
} from '@/types/api';
import type {
  ThesaurusEntry,
  WordSuggestionResponse,
} from '@/types';
import { api, transformError, API_BASE_URL } from './core';
import { logger } from '@/utils/logger';
import { SSEClient, type SSEOptions, type SSEHandlers } from './sse/SSEClient';

const sseClient = new SSEClient(api);

export const aiApi = {
  // Synthesis operations - POST /ai/synthesize/*
  synthesize: {
    // Generate synonyms - POST /ai/synthesize/synonyms
    async synonyms(word: string): Promise<ThesaurusEntry> {
      try {
        // Get word context from lookup
        const dictionaryEntryResponse = await api.get<DictionaryEntryResponse>(`/lookup/${encodeURIComponent(word)}`);

        // Safely extract entry data - handle both direct response and wrapped envelope shapes
        const entryData = dictionaryEntryResponse.data;
        if (!entryData) {
          throw new Error(`No data returned from lookup for "${word}"`);
        }

        // Extract definitions, handling potential response shape variations
        const definitions = entryData.definitions ?? (entryData as any).entry?.definitions;
        if (!definitions || !Array.isArray(definitions) || definitions.length === 0) {
          throw new Error(`No definitions found for "${word}"`);
        }

        const firstDefinition = definitions[0];

        // Call AI synthesis endpoint with consistent parameter structure
        const response = await api.post<AIResponse<{
          synonyms: Array<{ word: string; score: number }>;
          confidence: number;
        }>>('/ai/synthesize/synonyms', {
          word,
          definition: firstDefinition.text ?? '',
          part_of_speech: firstDefinition.part_of_speech ?? '',
          existing_synonyms: firstDefinition.synonyms ?? [],
          count: 10
        });

        // Safely extract AI result
        const result = response.data?.result;

        // Transform response to frontend format
        return {
          word,
          synonyms: result?.synonyms ?? [],
          confidence: result?.confidence ?? 0
        };
      } catch (error) {
        logger.error('Error fetching synonyms:', error);
        throw transformError(error);
      }
    },

    // Generate antonyms - POST /ai/synthesize/antonyms
    async antonyms(word: string, definition: string, partOfSpeech?: string): Promise<{
      word: string;
      antonyms: Array<{ word: string; score: number }>;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        antonyms: Array<{ word: string; score: number }>;
        confidence: number;
      }>>('/ai/synthesize/antonyms', {
        word,
        definition,
        part_of_speech: partOfSpeech,
        count: 10
      });

      const result = response.data?.result;
      return {
        word,
        antonyms: result?.antonyms ?? [],
        confidence: result?.confidence ?? 0
      };
    },

    // Generate pronunciation - POST /ai/synthesize/pronunciation
    async pronunciation(word: string): Promise<{
      word: string;
      phonetic: string;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        phonetic: string;
        confidence: number;
      }>>('/ai/synthesize/pronunciation', { word });

      return {
        word,
        phonetic: response.data.result.phonetic,
        confidence: response.data.result.confidence || 0
      };
    },
  },

  // Generation operations - POST /ai/generate/*
  generate: {
    // Generate examples - POST /ai/generate/examples
    async examples(
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

    // Generate facts - POST /ai/generate/facts
    async facts(word: string, definition?: string): Promise<{
      word: string;
      facts: Array<{ text: string; category: string; confidence: number }>;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        facts: Array<{ text: string; category: string; confidence: number }>;
        confidence: number;
      }>>('/ai/generate/facts', {
        word,
        definition
      });

      return {
        word,
        facts: response.data.result.facts || [],
        confidence: response.data.result.confidence || 0
      };
    },

    // Generate word forms - POST /ai/generate/word-forms
    async wordForms(word: string, partOfSpeech?: string): Promise<{
      word: string;
      forms: Record<string, string>;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        forms: Record<string, string>;
        confidence: number;
      }>>('/ai/generate/word-forms', {
        word,
        part_of_speech: partOfSpeech
      });

      return {
        word,
        forms: response.data.result.forms || {},
        confidence: response.data.result.confidence || 0
      };
    },
  },

  // Assessment operations - POST /ai/assess/*
  assess: {
    // Assess frequency band - POST /ai/assess/frequency
    async frequency(word: string): Promise<{
      word: string;
      frequency_band: number;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        frequency_band: number;
        confidence: number;
      }>>('/ai/assess/frequency', { word });

      return {
        word,
        frequency_band: response.data.result.frequency_band,
        confidence: response.data.result.confidence || 0
      };
    },

    // Assess CEFR level - POST /ai/assess/cefr
    async cefr(word: string, definition?: string): Promise<{
      word: string;
      cefr_level: string;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        cefr_level: string;
        confidence: number;
      }>>('/ai/assess/cefr', {
        word,
        definition
      });

      return {
        word,
        cefr_level: response.data.result.cefr_level,
        confidence: response.data.result.confidence || 0
      };
    },

    // Assess language register - POST /ai/assess/register
    async register(word: string, definition?: string): Promise<{
      word: string;
      register: string;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        register: string;
        confidence: number;
      }>>('/ai/assess/register', {
        word,
        definition
      });

      return {
        word,
        register: response.data.result.register,
        confidence: response.data.result.confidence || 0
      };
    },

    // Assess domain - POST /ai/assess/domain
    async domain(word: string, definition?: string): Promise<{
      word: string;
      domain: string;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        domain: string;
        confidence: number;
      }>>('/ai/assess/domain', {
        word,
        definition
      });

      return {
        word,
        domain: response.data.result.domain,
        confidence: response.data.result.confidence || 0
      };
    },

    // Assess collocations - POST /ai/assess/collocations
    async collocations(word: string, definition?: string): Promise<{
      word: string;
      collocations: Array<{ phrase: string; frequency: number }>;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        collocations: Array<{ phrase: string; frequency: number }>;
        confidence: number;
      }>>('/ai/assess/collocations', {
        word,
        definition
      });

      return {
        word,
        collocations: response.data.result.collocations || [],
        confidence: response.data.result.confidence || 0
      };
    },

    // Assess grammar patterns - POST /ai/assess/grammar-patterns
    async grammarPatterns(word: string, definition?: string): Promise<{
      word: string;
      patterns: Array<{ pattern: string; examples: string[] }>;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        patterns: Array<{ pattern: string; examples: string[] }>;
        confidence: number;
      }>>('/ai/assess/grammar-patterns', {
        word,
        definition
      });

      return {
        word,
        patterns: response.data.result.patterns || [],
        confidence: response.data.result.confidence || 0
      };
    },

    // Assess regional variants - POST /ai/assess/regional-variants
    async regionalVariants(word: string): Promise<{
      word: string;
      variants: Array<{ region: string; variant: string; usage: string }>;
      confidence: number;
    }> {
      const response = await api.post<AIResponse<{
        variants: Array<{ region: string; variant: string; usage: string }>;
        confidence: number;
      }>>('/ai/assess/regional-variants', { word });

      return {
        word,
        variants: response.data.result.variants || [],
        confidence: response.data.result.confidence || 0
      };
    },
  },

  // Validate query - POST /ai/validate-query
  async validateQuery(query: string): Promise<{
    valid: boolean;
    suggestions?: string[];
    issues?: string[];
  }> {
    const response = await api.post<AIResponse<{
      valid: boolean;
      suggestions?: string[];
      issues?: string[];
    }>>('/ai/validate-query', { query });

    return response.data.result;
  },

  // Generate usage notes - POST /ai/usage-notes
  async generateUsageNotes(word: string, definition?: string): Promise<{
    word: string;
    notes: Array<{ category: string; note: string }>;
    confidence: number;
  }> {
    const response = await api.post<AIResponse<{
      notes: Array<{ category: string; note: string }>;
      confidence: number;
    }>>('/ai/usage-notes', {
      word,
      definition
    });

    return {
      word,
      notes: response.data.result.notes || [],
      confidence: response.data.result.confidence || 0
    };
  },

  // Synthesize entire entry - POST /ai/synthesize
  async synthesizeEntry(word: string, options?: {
    components?: string[];
    force?: boolean;
  }): Promise<any> {
    const response = await api.post('/ai/synthesize', {
      word,
      components: options?.components || ['all'],
      force: options?.force || false
    });
    return response.data;
  },

  // Word suggestions - POST /ai/suggest-words
  async suggestWords(query: string, count: number = 12): Promise<WordSuggestionResponse> {
    // Cap count at 25 (backend limit)
    const cappedCount = Math.min(Math.max(count, 1), 25);
    const response = await api.post('/ai/suggest-words', {
      query,
      count: cappedCount
    });
    return response.data;
  },

  // Word suggestions with streaming - GET /ai/suggest-words/stream
  async suggestWordsStream(
    query: string,
    count: number = 12,
    onProgress?: (stage: string, progress: number, message?: string, details?: any) => void,
    onConfig?: (category: string, stages: Array<{progress: number, label: string, description: string}>) => void
  ): Promise<WordSuggestionResponse> {
    // Cap count at 25 (backend limit)
    const cappedCount = Math.min(Math.max(count, 1), 25);
    const params = new URLSearchParams({
      query: query,
      count: cappedCount.toString()
    });
    
    const url = `${API_BASE_URL}/ai/suggest-words/stream?${params.toString()}`;

    const sseOptions: SSEOptions = {
      timeout: 30000, // 30 seconds for AI suggestions
      onProgress: onProgress ? (event) => onProgress(event.stage, event.progress, event.message, event.details) : undefined,
      onConfig: onConfig ? (event) => onConfig(event.category, event.stages) : undefined
    };

    const handlers: SSEHandlers<WordSuggestionResponse> = {
      onEvent: (event: string, data: any) => {
        if (event === 'completion' || event === 'complete') {
          return data.result || data;
        }
        return null;
      },
      onComplete: () => {},
      onError: (error: Error) => {
        logger.error('AI suggestions stream error:', error);
      }
    };

    return sseClient.stream(url, sseOptions, handlers);
  },
};
