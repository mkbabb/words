import type {
  DictionaryEntryResponse,
  DictionaryProvider,
  Language,
} from '@/types/api';
import type { SynthesizedDictionaryEntry } from '@/types';
import { api, transformError, API_BASE_URL } from './core';

export const lookupApi = {
  // Main word lookup - GET /lookup/{word}
  async lookup(
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

  // Streaming word lookup - GET /lookup/{word}/stream
  async lookupStream(
    word: string,
    forceRefresh: boolean = false,
    providers?: DictionaryProvider[],
    languages?: Language[],
    onProgress?: (stage: string, progress: number, message: string, details?: any) => void,
    onConfig?: (category: string, stages: Array<{progress: number, label: string, description: string}>) => void,
    onPartialResult?: (partialEntry: Partial<SynthesizedDictionaryEntry>) => void,
    noAI?: boolean
  ): Promise<SynthesizedDictionaryEntry> {
    return new Promise(async (resolve, reject) => {
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
      
      console.log(`Opening fetch-based SSE connection to: ${url}`);

      let hasReceivedData = false;
      let connectionTimeout: NodeJS.Timeout;
      let partialResult: Partial<SynthesizedDictionaryEntry> = {};
      let definitions: any[] = [];
      let isChunkedCompletion = false;
      let abortController = new AbortController();
      
      // Set a timeout for initial connection (2 minutes for complex AI processing)
      connectionTimeout = setTimeout(() => {
        if (!hasReceivedData) {
          console.error('SSE connection timeout - no data received within 2 minutes');
          abortController.abort();
          reject(new Error('Connection timeout. Please try again.'));
        }
      }, 120000);

      try {
        // Use fetch with streaming instead of EventSource for better proxy compatibility
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

        console.log('Fetch-based SSE connection established successfully');

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        // Process the stream
        let currentEvent = '';
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            console.log('Stream completed');
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
              // Empty line ends an event in SSE format - reset current event
              if (currentEvent) {
                console.log(`End of SSE event: ${currentEvent}`);
              }
              currentEvent = '';
              continue;
            }
            
            // Parse SSE format: "event: eventname" or "data: {...}"
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7); // Remove "event: " prefix
              console.log('SSE Event:', currentEvent);
              continue;
            } else if (line.startsWith('data: ')) {
              const eventData = line.slice(6); // Remove "data: " prefix
              console.log(`SSE Data (event=${currentEvent}):`, eventData.substring(0, 100) + (eventData.length > 100 ? '...' : ''));
              
              try {
                const data = JSON.parse(eventData);
                
                // Handle completion event specially
                if (currentEvent === 'complete') {
                  console.log('✅ Completion event received:', { hasResult: !!data.result, isChunked: !!data.chunked, isChunkedCompletion, definitionsCount: definitions.length });
                  clearTimeout(connectionTimeout);
                  
                  if (data.result) {
                    // Single completion with result data
                    console.log('📦 Single completion with result data');
                    const result = data.result;
                    
                    const synthesizedEntry: SynthesizedDictionaryEntry = {
                      ...result,
                      lookup_count: 0,
                      regeneration_count: 0,
                      status: 'active'
                    };
                    
                    resolve(synthesizedEntry);
                    return;
                  } else if (data.chunked && isChunkedCompletion) {
                    // Chunked completion - use accumulated data
                    console.log('🧩 Chunked completion - assembling result:', { definitionsCount: definitions.length, hasPartialResult: !!partialResult });
                    const synthesizedEntry: SynthesizedDictionaryEntry = {
                      ...partialResult,
                      definitions,
                      lookup_count: 0,
                      regeneration_count: 0,
                      status: 'active'
                    } as SynthesizedDictionaryEntry;
                    
                    resolve(synthesizedEntry);
                    return;
                  } else {
                    console.log('⚠️ Completion event without result or chunked data');
                  }
                } else if (currentEvent === 'completion_start') {
                  // Handle chunked completion start
                  isChunkedCompletion = true;
                  console.log('🚀 Starting chunked completion:', data);
                } else if (currentEvent === 'completion_chunk') {
                  // Handle chunked completion data
                    if (data.chunk_type === 'basic_info') {
                      // Merge basic info into partial result
                      partialResult = {
                        ...partialResult,
                        ...data.data,
                        lookup_count: 0,
                        regeneration_count: 0,
                        status: 'active'
                      };
                      
                      // Stream basic info to UI
                      if (onPartialResult) {
                        onPartialResult({ ...partialResult, definitions });
                      }
                    } else if (data.chunk_type === 'definition') {
                      // Add or update definition (without examples for now)
                      const defIndex = data.definition_index;
                      if (!definitions[defIndex]) {
                        definitions[defIndex] = { ...data.data, examples: [] };
                      } else {
                        definitions[defIndex] = { ...definitions[defIndex], ...data.data };
                      }
                      
                      // Stream updated definition to UI
                      if (onPartialResult) {
                        onPartialResult({ ...partialResult, definitions: [...definitions] });
                      }
                    } else if (data.chunk_type === 'examples') {
                      // Add examples to the appropriate definition
                      const defIndex = data.definition_index;
                      if (definitions[defIndex]) {
                        if (!definitions[defIndex].examples) {
                          definitions[defIndex].examples = [];
                        }
                        definitions[defIndex].examples.push(...data.data);
                        
                        // Stream updated examples to UI
                        if (onPartialResult) {
                          onPartialResult({ ...partialResult, definitions: [...definitions] });
                        }
                      }
                    }
                } else {
                  // Handle regular data events based on data.type
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
                console.error('Error parsing SSE data:', parseError, 'Raw data:', eventData);
              }
            }
          }
        }

        // If we have chunked completion data, resolve with accumulated result
        if (isChunkedCompletion && partialResult && definitions.length > 0) {
          console.log('🔄 Stream ended with chunked completion data, resolving fallback completion:', { definitionsCount: definitions.length, hasPartialResult: !!partialResult });
          const synthesizedEntry: SynthesizedDictionaryEntry = {
            ...partialResult,
            definitions,
            lookup_count: 0,
            regeneration_count: 0,
            status: 'active'
          } as SynthesizedDictionaryEntry;
          
          resolve(synthesizedEntry);
          return;
        }

        // If we get here without resolving, something went wrong
        reject(new Error('Stream ended without completion event'));

      } catch (error) {
        clearTimeout(connectionTimeout);
        console.error('Fetch-based SSE connection error:', error);
        
        // If we haven't received any data, it might be a connection issue
        if (!hasReceivedData) {
          reject(new Error(`Failed to establish SSE connection: ${error instanceof Error ? error.message : String(error)}. Please try again.`));
        } else {
          reject(new Error('Stream connection lost'));
        }
      }
    });
  },
};