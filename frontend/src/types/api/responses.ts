/**
 * Backend API Type Definitions - Response Envelopes
 *
 * API response wrappers, search responses, health checks,
 * and feature-specific response types.
 */

import type {
    AudioFile,
    Definition,
    Etymology,
    Example,
    ImageMedia,
    Language,
    ModelInfo,
    SearchMethod,
    DictionaryProvider,
} from './models';

// Generic API Response Types
export interface ListResponse<T> {
    items: T[];
    total: number;
    offset: number;
    limit: number;
    has_more: boolean;
}

export interface ResourceResponse<T = any> {
    data: T;
    metadata?: {
        version: number;
        last_modified: string;
        [key: string]: any;
    };
    links?: {
        self: string;
        related?: string;
        [key: string]: string | undefined;
    };
}

export interface ErrorResponse {
    error: string;
    details?: Array<{
        field?: string;
        message: string;
        code?: string;
    }>;
    timestamp: string;
    request_id?: string;
}

// Dictionary Entry Response Types
export interface DictionaryEntryResponse {
    word: string;
    languages: Language[];
    pronunciation?: {
        phonetic: string;
        ipa: string;
        audio_files: AudioFile[];
        syllables: string[];
        stress_pattern?: string;
    };
    definitions: Array<
        Definition & {
            examples: Example[]; // Always populated
            images: ImageMedia[]; // Always populated
            providers_data: Array<Record<string, any>>;
        }
    >;
    etymology?: Etymology;
    last_updated: string;
    model_info?: ModelInfo | null;
    id?: string | null;
    images?: ImageMedia[];
}

// Search Response Types
export interface SearchResult {
    word: string;
    score: number; // 0.0-1.0
    method: SearchMethod;
    is_phrase: boolean;
}

export interface SearchResponse {
    query: string;
    results: SearchResult[];
    total_found: number;
    languages: Language[];
}

// Streaming Progress Types
export interface ProgressEvent {
    stage: 'SEARCH' | 'FETCH' | 'SYNTHESIZE' | 'COMPLETE';
    progress: number; // 0-100
    message: string;
    details?: any;
}

// Semantic Status Types
export interface SemanticStatusResponse {
    enabled: boolean;
    ready: boolean;
    building: boolean;
    languages: Language[];
    model_name: string | null;
    vocabulary_size: number;
    message: string;
}

// Health Check Types
export interface HealthResponse {
    status: 'healthy' | 'degraded';
    version?: string | null;
    services: Record<string, string>;
    metrics: Record<string, any>;
    timestamp: string;
    database: 'connected' | 'disconnected' | 'unhealthy';
    search_engine: 'initialized' | 'uninitialized' | 'initializing' | 'error';
    cache_hit_rate: number;
    uptime_seconds: number;
    connection_pool: Record<string, any>;
}

// AI API Types
export interface AIRequest {
    word: string;
    definitions?: string[];
    context?: string;
    options?: Record<string, any>;
}

export interface AIResponse<T = any> {
    result: T;
    model_info: ModelInfo;
    usage?: {
        prompt_tokens: number;
        completion_tokens: number;
        total_tokens: number;
    };
}

// Batch API Types
export interface BatchLookupRequest {
    words: string[];
    options?: {
        force_refresh?: boolean;
        providers?: DictionaryProvider[];
        languages?: Language[];
        no_ai?: boolean;
    };
}

export interface BatchDictionaryEntryResponse {
    results: Array<{
        word: string;
        success: boolean;
        data?: DictionaryEntryResponse;
        error?: string;
    }>;
    summary: {
        total: number;
        successful: number;
        failed: number;
    };
}
