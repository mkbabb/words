/**
 * Backend API Type Definitions - Core Models
 *
 * Enums, core entities, and domain models isomorphic to backend Pydantic models.
 */

// Enums and Constants - Isomorphic to backend
export enum Language {
    ENGLISH = 'en',
    FRENCH = 'fr',
    SPANISH = 'es',
    GERMAN = 'de',
    ITALIAN = 'it',
}

export enum DictionaryProvider {
    WIKTIONARY = 'wiktionary',
    OXFORD = 'oxford',
    MERRIAM_WEBSTER = 'merriam_webster',
    FREE_DICTIONARY = 'free_dictionary',
    WORDHIPPO = 'wordhippo',
    APPLE_DICTIONARY = 'apple_dictionary',
    AI_FALLBACK = 'ai_fallback',
    SYNTHESIS = 'synthesis',
}

// SearchMethod: what method produced the result (on each SearchResult)
export enum SearchMethod {
    EXACT = 'exact',
    PREFIX = 'prefix',
    SUBSTRING = 'substring',
    FUZZY = 'fuzzy',
    SEMANTIC = 'semantic',
    AUTO = 'auto',
}

// SearchMode: what the user requested (query parameter)
export enum SearchMode {
    SMART = 'smart',
    EXACT = 'exact',
    FUZZY = 'fuzzy',
    SEMANTIC = 'semantic',
}

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
    languages: Language[];
    homograph_number?: number;
    offensive_flag: boolean;
    first_known_use?: string;
}

// Relationship Models
export interface WordForm {
    form_type:
        | 'plural'
        | 'past'
        | 'past_participle'
        | 'present_participle'
        | 'comparative'
        | 'superlative'
        | 'variant';
    text: string;
}

export interface MeaningCluster {
    id: string; // UUID primary key
    slug: string; // Human-readable: "bank_noun_financial"
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

// Provenance — links synthesized content to source provider data
export interface SourceReference {
    provider: DictionaryProvider;
    entry_id: string;
    entry_version: string;
    definition_ids: string[];
    richness_score?: number;
}

export interface SourceVersionSpec {
    provider: string;
    version: string;
}

// Etymology
export interface Etymology {
    text: string;
    language?: string;
    period?: string;
}

// Synonym Chooser — MW-style comparative essay
export interface SynonymComparison {
    word: string;
    distinction: string;
}

export interface SynonymChooser {
    essay: string;
    synonyms_compared: SynonymComparison[];
    model_info?: ModelInfo;
}

// Phrase/Idiom
export interface Phrase {
    phrase: string;
    meaning: string;
    example?: string;
    usage_register?: string; // formal, informal, literary, archaic
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
    language_register?:
        | 'formal'
        | 'informal'
        | 'neutral'
        | 'slang'
        | 'technical';
    domain?: string;
    region?: string;
    usage_notes: UsageNote[];
    grammar_patterns: GrammarPattern[];
    collocations: Collocation[];
    transitivity?: 'transitive' | 'intransitive' | 'both';
    cefr_level?: 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2';
    frequency_band?: number; // 1-5
    frequency_score?: number; // 0.0-1.0 continuous, for temperature visualization
    accessed_at?: string;
    created_by?: string;
    updated_by?: string;
    source_attribution?: string;
    quality_score?: number;
    relevancy?: number;
    validation_status?: string;
    metadata: Record<string, any>;
    providers_data?: Record<string, any>; // Provider-specific data from dictionary sources
    source_definitions?: SourceReference[]; // Provenance: which provider defs contributed
}

// Synthesized Entry
export interface SynthesizedDictionaryEntry extends BaseMetadata {
    id: string;
    word_id: string;
    word: string; // The word text (populated in responses)
    languages: string[]; // Language precedence list (primary first)
    pronunciation_id?: string;
    pronunciation?: Pronunciation; // Populated in responses
    definition_ids: string[];
    definitions?: Definition[]; // Populated in responses
    etymology?: Etymology;
    synonym_chooser?: SynonymChooser; // Comparative synonym essay
    phrases?: Phrase[]; // Phrases & idioms
    fact_ids: string[];
    image_ids: string[];
    images?: ImageMedia[]; // Populated in responses
    model_info?: ModelInfo | null;
    richness_score?: number;
    source_provider_data_ids: string[];
    source_entries?: SourceReference[]; // Provenance: which provider entries fed synthesis
    accessed_at?: string;
    access_count: number;
    last_updated: string; // Alias for updated_at for frontend compatibility
}

// User & Auth Types
export type UserRole = 'user' | 'premium' | 'admin';

export interface UserProfile {
    clerk_id: string;
    email: string | null;
    username: string | null;
    avatar_url: string | null;
    role: UserRole;
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
    search_history: Array<{
        query: string;
        timestamp: string;
        [key: string]: any;
    }>;
    lookup_history: Array<{
        word: string;
        timestamp: string;
        [key: string]: any;
    }>;
    updated_at?: string;
}

// Utility Types
export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
export type RequiredFields<T, K extends keyof T> = Omit<T, K> &
    Required<Pick<T, K>>;
