import type {
  AIResponse,
  DictionaryEntryResponse,
} from '@/types/api';
import type {
  ThesaurusEntry,
  WordSuggestionResponse,
} from '@/types';
import { api, transformError, API_BASE_URL } from './core';

export const aiApi = {
  // Synthesis operations - POST /ai/synthesize/*
  synthesize: {
    // Generate synonyms - POST /ai/synthesize/synonyms
    async synonyms(word: string): Promise<ThesaurusEntry> {
      try {
        // Get word context from lookup
        const dictionaryEntryResponse = await api.get<DictionaryEntryResponse>(`/lookup/${encodeURIComponent(word)}`);
        
        if (!dictionaryEntryResponse.data?.definitions?.length) {
          throw new Error('No definitions found for word');
        }

        const firstDefinition = dictionaryEntryResponse.data.definitions[0];
        
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

      return {
        word,
        antonyms: response.data.result.antonyms || [],
        confidence: response.data.result.confidence || 0
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
    return new Promise(async (resolve, reject) => {
      // Cap count at 25 (backend limit)
      const cappedCount = Math.min(Math.max(count, 1), 25);
      const params = new URLSearchParams({
        query: query,
        count: cappedCount.toString()
      });
      
      const url = `${API_BASE_URL}/ai/suggest-words/stream?${params.toString()}`;
      console.log(`Opening fetch-based SSE connection for AI suggestions to: ${url}`);

      let hasReceivedData = false;
      let connectionTimeout: NodeJS.Timeout;
      let abortController = new AbortController();
      
      // Set connection timeout (AI suggestions are usually faster)
      connectionTimeout = setTimeout(() => {
        if (!hasReceivedData) {
          console.error('AI suggestions SSE connection timeout');
          abortController.abort();
          reject(new Error('Connection timeout'));
        }
      }, 30000); // 30 seconds for AI suggestions

      try {
        // Use fetch with streaming instead of EventSource
        const response = await fetch(url, {
          method: 'GET',
          headers: {
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          signal: abortController.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        if (!response.body) {
          throw new Error('No response body received');
        }

        console.log('AI suggestions fetch-based SSE connection established successfully');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // Process the stream
        let currentEvent = '';
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            console.log('AI suggestions stream completed');
            break;
          }

          hasReceivedData = true;
          clearTimeout(connectionTimeout);

          // Decode the chunk and add to buffer
          buffer += decoder.decode(value, { stream: true });
          
          // Process complete lines
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer
          
          for (const line of lines) {
            if (line.trim() === '') {
              // Empty line ends an event in SSE format
              currentEvent = '';
              continue;
            }
            
            // Parse SSE format: "event: eventname" or "data: {...}"
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7); // Remove "event: " prefix
              console.log('AI Suggestions SSE Event:', currentEvent);
              continue;
            } else if (line.startsWith('data: ')) {
              const eventData = line.slice(6); // Remove "data: " prefix
              
              try {
                const data = JSON.parse(eventData);
                
                // Handle completion event specially
                if (currentEvent === 'complete') {
                  console.log('AI suggestions fetch-based SSE connection completed successfully');
                  clearTimeout(connectionTimeout);
                  
                  // Extract result from new structured format
                  const result = data.result || data;
                  resolve(result as WordSuggestionResponse);
                  return;
                } else {
                  // Handle different event types based on data.type
                  if (data.type === 'config') {
                    if (onConfig) {
                      onConfig(data.category, data.stages);
                    }
                  } else if (data.type === 'progress') {
                    if (onProgress) {
                      onProgress(data.stage, data.progress, data.message, data.details);
                    }
                  }
                }
              } catch (parseError) {
                console.error('Error parsing AI suggestions SSE data:', parseError, 'Raw data:', eventData);
              }
            }
          }
        }

        // Handle any remaining completion data in buffer
        if (buffer.trim()) {
          const lines = buffer.split('\n');
          let lastEvent = '';
          
          for (const line of lines) {
            if (line.startsWith('event: ')) {
              lastEvent = line.slice(7);
            } else if (line.startsWith('data: ') && lastEvent === 'complete') {
              try {
                const data = JSON.parse(line.slice(6));
                console.log('AI suggestions final completion from buffer');
                
                // Extract result from new structured format
                const result = data.result || data;
                resolve(result as WordSuggestionResponse);
                return;
              } catch (parseError) {
                console.error('Error parsing AI suggestions final completion data:', parseError);
              }
            }
          }
        }

        // If we get here without resolving, something went wrong
        reject(new Error('AI suggestions stream ended without completion event'));

      } catch (error) {
        clearTimeout(connectionTimeout);
        console.error('AI suggestions fetch-based SSE connection error:', error);
        
        // If we haven't received any data, it might be a connection issue
        if (!hasReceivedData) {
          reject(new Error(`Failed to establish AI suggestions SSE connection: ${error instanceof Error ? error.message : String(error)}`));
        } else {
          reject(new Error('AI suggestions stream connection lost'));
        }
      }
    });
  },
};
