import type { AxiosInstance } from 'axios'

// Backend-aligned SSE event types
export interface ProgressEvent {
  stage: string                    // Backend detailed stage names
  progress: number                 // 0-100
  message?: string                 // Human-readable status
  details?: Record<string, unknown> // Stage-specific details
  is_complete?: boolean            // Pipeline completion flag
  error?: string | null            // Error message if failed
}

export interface ConfigEvent {
  category: string
  stages: Array<{
    progress: number
    label: string
    description: string
  }>
}

export interface ChunkedCompletionStart {
  message: string
  total_definitions?: number
}

export interface ChunkedCompletionChunk {
  chunk_type: 'basic_info' | 'definition' | 'examples'
  definition_index?: number
  batch_start?: number
  data: unknown
}

export interface CompletionEvent {
  type?: 'complete' | 'error'
  message: string
  result?: unknown
  chunked?: boolean
}

export interface SSEOptions {
  timeout?: number
  signal?: AbortSignal
  onProgress?: (event: ProgressEvent) => void
  onPartialResult?: (data: unknown) => void
  onConfig?: (event: ConfigEvent) => void
}

export interface SSEHandlers<T> {
  onEvent: (event: string, data: unknown) => T | null
  onComplete: (result: T) => void
  onError?: (error: Error) => void
}

export class SSEClient {
  constructor(private axios: AxiosInstance) {}

  async stream<T>(
    url: string,
    options: SSEOptions,
    handlers: SSEHandlers<T>
  ): Promise<T> {
    return new Promise((resolve, reject) => {
      const controller = new AbortController()
      const timeout = options.timeout || 120000
      let hasReceivedData = false
      let timeoutId: NodeJS.Timeout

      const cleanup = () => {
        clearTimeout(timeoutId)
        controller.abort()
      }

      timeoutId = setTimeout(() => {
        cleanup()
        reject(new Error(`SSE connection timeout after ${timeout}ms`))
      }, timeout)

      this.processStream(url, controller.signal, options, handlers)
        .then(result => {
          cleanup()
          resolve(result)
        })
        .catch(error => {
          cleanup()
          if (!hasReceivedData) {
            reject(new Error(`Failed to establish SSE connection: ${error.message}`))
          } else {
            reject(error)
          }
        })
    })
  }

  private async processStream<T>(
    url: string,
    signal: AbortSignal,
    options: SSEOptions,
    handlers: SSEHandlers<T>
  ): Promise<T> {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Authorization': `Bearer ${this.axios.defaults.headers.common['Authorization']}`
      },
      signal
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body')
    }

    const decoder = new TextDecoder()
    let buffer = ''
    let currentEvent = ''
    let result: T | null = null
    let isChunkedCompletion = false
    let chunks: ChunkedCompletionChunk[] = []

    while (true) {
      const { done, value } = await reader.read()
      
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (line.trim() === '') {
          if (currentEvent) {
            currentEvent = ''
          }
          continue
        }

        if (line.startsWith('event: ')) {
          currentEvent = line.slice(7)
        } else if (line.startsWith('data: ')) {
          const data = this.parseData(line.slice(6))
          
          // Handle different event types
          switch (currentEvent) {
            case 'config':
              if (options.onConfig) {
                options.onConfig(data as ConfigEvent)
              }
              break
              
            case 'progress':
              if (options.onProgress) {
                const progressData = data as ProgressEvent
                options.onProgress(progressData)
              }
              break
              
            case 'completion_start':
              isChunkedCompletion = true
              chunks = []
              break
              
            case 'completion_chunk':
              if (isChunkedCompletion) {
                chunks.push(data as ChunkedCompletionChunk)
              }
              break
              
            case 'complete':
            case 'completion':
              if (isChunkedCompletion && chunks.length > 0) {
                // Assemble chunked result
                const assembled = this.assembleChunkedResult(chunks)
                result = handlers.onEvent('complete', assembled)
              } else {
                // Regular completion
                const completion = data as CompletionEvent
                result = handlers.onEvent('complete', completion.result || data)
              }
              
              if (result) {
                handlers.onComplete(result)
                return result
              }
              break
              
            case 'error':
              const errorData = data as { message?: string }
              const error = new Error(errorData.message || 'SSE stream error')
              if (handlers.onError) {
                handlers.onError(error)
              }
              throw error
              
            case 'partial':
              if (options.onPartialResult) {
                options.onPartialResult(data)
              }
              break
              
            default:
              // Let handler process unknown events
              const eventResult = handlers.onEvent(currentEvent, data)
              if (eventResult) {
                result = eventResult
              }
          }
        }
      }
    }

    if (result) {
      return result
    }

    throw new Error('Stream ended without completion event')
  }

  private parseData(dataString: string): unknown {
    if (dataString === '[DONE]') {
      return { done: true }
    }

    try {
      return JSON.parse(dataString)
    } catch {
      return dataString
    }
  }
  
  private assembleChunkedResult(chunks: ChunkedCompletionChunk[]): unknown {
    // Group chunks by type
    const basicInfo = chunks.find(c => c.chunk_type === 'basic_info')?.data || {}
    const definitions: unknown[] = []
    const examples: Map<number, unknown[]> = new Map()
    
    for (const chunk of chunks) {
      if (chunk.chunk_type === 'definition' && chunk.definition_index !== undefined) {
        definitions[chunk.definition_index] = chunk.data
      } else if (chunk.chunk_type === 'examples' && chunk.definition_index !== undefined) {
        const existing = examples.get(chunk.definition_index) || []
        existing.push(...(Array.isArray(chunk.data) ? chunk.data : [chunk.data]))
        examples.set(chunk.definition_index, existing)
      }
    }
    
    // Merge examples into definitions
    const mergedDefinitions = definitions.map((def, index) => {
      const defExamples = examples.get(index) || []
      return {
        ...(def as Record<string, unknown>),
        examples: defExamples
      }
    })
    
    // Assemble final result
    return {
      ...(basicInfo as Record<string, unknown>),
      definitions: mergedDefinitions
    }
  }
}