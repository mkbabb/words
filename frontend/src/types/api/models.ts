/**
 * Frontend-only API type definitions.
 *
 * Types with backend equivalents live in schemas.ts (generated from OpenAPI).
 * This file contains ONLY types that are frontend-exclusive or extend the
 * generated types with frontend-specific fields.
 */

import type {
    Language,
    ModelInfoResponse,
    SourceReference,
} from './schemas';

// ── Enums (no generated equivalent — backend uses string, not enum) ──

export enum SearchMethod {
    EXACT = 'exact',
    PREFIX = 'prefix',
    SUBSTRING = 'substring',
    FUZZY = 'fuzzy',
    SEMANTIC = 'semantic',
    AUTO = 'auto',
}

export enum SearchMode {
    SMART = 'smart',
    EXACT = 'exact',
    FUZZY = 'fuzzy',
    SEMANTIC = 'semantic',
}

// ── Base types (frontend convention, not a backend model) ───────────

export interface BaseMetadata {
    created_at: string;
    updated_at: string;
    version: number;
}

// ── Word (frontend extends with fields not in generated schema) ─────

export interface Word extends BaseMetadata {
    id: string;
    text: string;
    normalized: string;
    languages: Language[];
    homograph_number?: number;
    offensive_flag: boolean;
    first_known_use?: string;
}

// ── Etymology (embedded in response, not a standalone schema) ───────

export interface Etymology {
    text: string;
    language?: string;
    period?: string;
}

// ── Synonym Chooser (frontend-only, MW-style comparative essay) ─────

export interface SynonymComparison {
    word: string;
    distinction: string;
}

export interface SynonymChooser {
    essay: string;
    synonyms_compared: SynonymComparison[];
    model_info?: ModelInfoResponse;
}

// ── Phrase/Idiom (frontend-only model) ──────────────────────────────

export interface Phrase {
    phrase: string;
    meaning: string;
    example?: string;
    usage_register?: string;
}

// ── Literature Source (frontend-only, generated has different shape) ─

export interface LiteratureSource {
    title: string;
    author?: string;
    year?: number;
    url?: string;
}

// ── Example (frontend extends with literature source) ───────────────

export interface Example extends BaseMetadata {
    id: string;
    definition_id: string;
    text: string;
    type: 'generated' | 'literature';
    model_info?: ModelInfoResponse;
    context?: string;
    source?: LiteratureSource;
}

// ── Audio (frontend model, generated has AudioFileResponse) ─────────

export interface AudioFile {
    id: string;
    url: string;
    mime_type: string;
    accent?: string;
    gender?: string;
}

// ── Image (frontend extends with metadata) ──────────────────────────

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

// ── Pronunciation (frontend model with audio resolution) ────────────

export interface Pronunciation extends BaseMetadata {
    id: string;
    word_id: string;
    phonetic: string;
    ipa: string;
    audio_file_ids: string[];
    audio_files?: AudioFile[];
    syllables: string[];
    stress_pattern?: string;
}

// ── Definition (frontend extends heavily) ───────────────────────────

export interface Definition extends BaseMetadata {
    id: string;
    word_id: string;
    part_of_speech: string;
    text: string;
    meaning_cluster?: {
        id?: string;
        slug?: string;
        name?: string;
        description?: string;
        order?: number;
        relevance?: number;
    };
    sense_number?: string;
    word_forms: Array<{ form_type: string; text: string }>;
    example_ids: string[];
    examples?: Example[];
    image_ids: string[];
    images?: ImageMedia[];
    synonyms: string[];
    antonyms: string[];
    language_register?: 'formal' | 'informal' | 'neutral' | 'slang' | 'technical';
    domain?: string;
    region?: string;
    usage_notes: Array<{ type?: string; text: string }>;
    grammar_patterns: Array<{ pattern: string; description?: string; examples?: string[] }>;
    collocations: Array<{ text: string; frequency?: string; type?: string }>;
    transitivity?: 'transitive' | 'intransitive' | 'both';
    cefr_level?: 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2';
    frequency_band?: number;
    frequency_score?: number;
    accessed_at?: string;
    created_by?: string;
    updated_by?: string;
    source_attribution?: string;
    quality_score?: number;
    relevancy?: number;
    validation_status?: string;
    metadata: Record<string, any>;
    providers_data?: Array<Record<string, any>>;
    source_definitions?: SourceReference[];
}

// ── Synthesized Entry (frontend wrapper around DictionaryEntryResponse) ──

export interface SynthesizedDictionaryEntry extends BaseMetadata {
    id: string;
    word_id: string;
    word: string;
    languages: string[];
    pronunciation_id?: string;
    pronunciation?: Pronunciation;
    definition_ids: string[];
    definitions?: Definition[];
    etymology?: Etymology;
    synonym_chooser?: SynonymChooser;
    phrases?: Phrase[];
    fact_ids: string[];
    image_ids: string[];
    images?: ImageMedia[];
    model_info?: ModelInfoResponse | null;
    richness_score?: number;
    source_provider_data_ids: string[];
    source_entries?: SourceReference[];
    accessed_at?: string;
    access_count: number;
    last_updated: string;
}

// ── User types ──────────────────────────────────────────────────────

export interface UserProfile {
    clerk_id: string;
    email: string | null;
    username: string | null;
    avatar_url: string | null;
    role: 'user' | 'premium' | 'admin';
    preferences: UserPreferences;
    created_at: string;
    last_login: string;
}

export interface UserPreferences {
    theme?: string;
    searchMode?: string;
    providers?: string[];
    language?: string;
    [key: string]: any;
}

export interface UserHistoryData {
    search_history: Array<{ query: string; timestamp: string; [key: string]: any }>;
    lookup_history: Array<{ word: string; timestamp: string; [key: string]: any }>;
    updated_at?: string;
}

// ── Utility types ───────────────────────────────────────────────────

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = Omit<T, K> & Required<Pick<T, K>>;
