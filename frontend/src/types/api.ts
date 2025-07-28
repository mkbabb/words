/**
 * Backend API Type Definitions
 * 
 * These types are isomorphic to the backend Pydantic models
 * and represent the exact shape of data returned by the API.
 */

// Enums and Constants
export type Language = 'en' | 'es' | 'fr' | 'de' | 'it' | 'pt' | 'ru' | 'ja' | 'zh' | 'ar';
export type DictionaryProvider = 'wiktionary' | 'oxford' | 'dictionary_com' | 'merriam_webster';
export type SearchMethod = 'EXACT' | 'FUZZY' | 'SEMANTIC' | 'PHONETIC' | 'AI';

// Base Metadata
export interface BaseMetadata {
  created_at: string; // ISO datetime
  updated_at: string; // ISO datetime
  version: number;
}

// Word Models
export interface Word extends BaseMetadata {
  id: string;
  text: string;
  normalized: string;
  language: Language;
  homograph_number?: number;
  offensive_flag: boolean;
  first_known_use?: string;
}

// Relationship Models
export interface WordForm {
  form_type: 'plural' | 'past' | 'past_participle' | 'present_participle' | 'comparative' | 'superlative' | 'variant';
  text: string;
}

export interface MeaningCluster {
  id: string;
  name: string;
  description: string;
  order: number;
  relevance: number; // 0.0-1.0
}

export interface UsageNote {
  type: 'grammar' | 'confusion' | 'regional' | 'register' | 'error';
  text: string;
}

export interface GrammarPattern {
  pattern: string;
  description?: string;
}

export interface Collocation {
  text: string;
  type: string;
  frequency: number; // 0.0-1.0
}

// Etymology
export interface Etymology {
  text: string;
  language?: string;
  period?: string;
}

// Model Info (for AI-generated content)
export interface ModelInfo {
  name: string;
  confidence: number;
  temperature: number;
  generation_count: number;
  last_generated: string;
}

// Literature Source
export interface LiteratureSource {
  title: string;
  author?: string;
  year?: number;
  url?: string;
}

// Example
export interface Example extends BaseMetadata {
  id: string;
  definition_id: string;
  text: string;
  type: 'generated' | 'literature';
  model_info?: ModelInfo;
  context?: string;
  source?: LiteratureSource;
}

// Media
export interface AudioFile {
  id: string;
  url: string;
  mime_type: string;
  accent?: string;
  gender?: string;
}

export interface ImageMedia extends BaseMetadata {
  id: string;
  url: string;
  format: string;
  size_bytes: number;
  width: number;
  height: number;
  alt_text?: string;
  description?: string;
}

// Pronunciation
export interface Pronunciation extends BaseMetadata {
  id: string;
  word_id: string;
  phonetic: string;
  ipa: string;
  audio_file_ids: string[];
  audio_files?: AudioFile[]; // Populated in responses
  syllables: string[];
  stress_pattern?: string;
}

// Definition
export interface Definition extends BaseMetadata {
  id: string;
  word_id: string;
  part_of_speech: string;
  text: string;
  meaning_cluster?: MeaningCluster;
  sense_number?: string;
  word_forms: WordForm[];
  example_ids: string[];
  examples?: Example[]; // Populated in responses
  image_ids: string[];
  images?: ImageMedia[]; // Populated in responses
  synonyms: string[];
  antonyms: string[];
  language_register?: 'formal' | 'informal' | 'neutral' | 'slang' | 'technical';
  domain?: string;
  region?: string;
  usage_notes: UsageNote[];
  grammar_patterns: GrammarPattern[];
  collocations: Collocation[];
  transitivity?: 'transitive' | 'intransitive' | 'both';
  cefr_level?: 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2';
  frequency_band?: number; // 1-5
  accessed_at?: string;
  created_by?: string;
  updated_by?: string;
  source_attribution?: string;
  quality_score?: number;
  relevancy?: number;
  validation_status?: string;
  metadata: Record<string, any>;
}

// Synthesized Entry
export interface SynthesizedDictionaryEntry extends BaseMetadata {
  id: string;
  word_id: string;
  pronunciation_id?: string;
  pronunciation?: Pronunciation; // Populated in responses
  definition_ids: string[];
  definitions?: Definition[]; // Populated in responses
  etymology?: Etymology;
  fact_ids: string[];
  image_ids: string[];
  images?: ImageMedia[]; // Populated in responses
  model_info?: ModelInfo | null;
  source_provider_data_ids: string[];
  accessed_at?: string;
  access_count: number;
}

// API Response Types
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

// Lookup Response Types
export interface LookupResponse {
  word: string;
  pronunciation?: {
    phonetic: string;
    ipa: string;
    audio_files: AudioFile[];
    syllables: string[];
    stress_pattern?: string;
  };
  definitions: DefinitionResponse[];
  last_updated: string;
  pipeline_metrics?: PipelineMetrics;
  model_info?: ModelInfo | null;
  synth_entry_id?: string | null;
  images?: ImageMedia[];
}

export interface DefinitionResponse extends Definition {
  examples: Example[]; // Always populated
  images: ImageMedia[]; // Always populated
  providers_data: Array<Record<string, any>>;
}

export interface PipelineMetrics {
  total_duration_ms: number;
  stages: Record<string, {
    duration_ms: number;
    success: boolean;
    details?: any;
  }>;
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
  language: Language;
}

// Streaming Progress Types
export interface ProgressEvent {
  stage: 'SEARCH' | 'FETCH' | 'SYNTHESIZE' | 'COMPLETE';
  progress: number; // 0-100
  message: string;
  details?: any;
}

// Health Check Types
export interface HealthResponse {
  status: 'healthy' | 'degraded';
  database: 'connected' | 'disconnected' | 'unhealthy';
  search_engine: 'initialized' | 'uninitialized';
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

export interface BatchLookupResponse {
  results: Array<{
    word: string;
    success: boolean;
    data?: LookupResponse;
    error?: string;
  }>;
  summary: {
    total: number;
    successful: number;
    failed: number;
  };
}

// Type Guards
export function isWord(obj: any): obj is Word {
  return obj && typeof obj.text === 'string' && typeof obj.normalized === 'string';
}

export function isDefinition(obj: any): obj is Definition {
  return obj && typeof obj.word_id === 'string' && typeof obj.part_of_speech === 'string';
}

export function isExample(obj: any): obj is Example {
  return obj && typeof obj.text === 'string' && (obj.type === 'generated' || obj.type === 'literature');
}

export function isMeaningCluster(obj: any): obj is MeaningCluster {
  return obj && typeof obj.id === 'string' && typeof obj.name === 'string';
}

// Utility Types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;