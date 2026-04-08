/**
 * Flat type aliases from the auto-generated OpenAPI types.
 *
 * This file is the ONLY place consumers should import backend-derived types.
 * It re-exports generated schemas with ergonomic names and provides const
 * objects for enum-like union types (Language.ENGLISH, DictionaryProvider.WIKTIONARY).
 *
 * Regenerate the source: `npm run generate-api-types`
 * Then update this file if schemas were added/renamed/removed.
 */

import type { components } from './generated';

// ── Enum-like union types ───────────────────────────────────────────
// openapi-typescript generates union types, not TS enums.
// Const objects provide runtime value access while the type is the union.

export type Language = components['schemas']['Language'];
export const Language = {
    ENGLISH: 'en',
    FRENCH: 'fr',
    SPANISH: 'es',
    GERMAN: 'de',
    ITALIAN: 'it',
} as const satisfies Record<string, Language>;

export type DictionaryProvider = components['schemas']['DictionaryProvider'];
export const DictionaryProvider = {
    WIKTIONARY: 'wiktionary',
    OXFORD: 'oxford',
    APPLE_DICTIONARY: 'apple_dictionary',
    MERRIAM_WEBSTER: 'merriam_webster',
    FREE_DICTIONARY: 'free_dictionary',
    WORDHIPPO: 'wordhippo',
    WORDNET: 'wordnet',
    GCIDE: 'gcide',
    WIKIPEDIA: 'wikipedia',
    MOBY_THESAURUS: 'moby_thesaurus',
    AI_FALLBACK: 'ai_fallback',
    SYNTHESIS: 'synthesis',
} as const satisfies Record<string, DictionaryProvider>;

export type UserRole = components['schemas']['UserRole'];
export const UserRole = {
    USER: 'user',
    PREMIUM: 'premium',
    ADMIN: 'admin',
} as const satisfies Record<string, UserRole>;

// ── Entry response types ────────────────────────────────────────────
// DictionaryEntryResponse is kept in responses.ts — the generated version
// has nullable sub-fields that don't match the frontend's expected shape.
// As the backend types improve, this can migrate to the generated version.
export type DefinitionResponse = components['schemas']['DefinitionResponse-Output'];
export type PronunciationResponse = components['schemas']['floridify__api__routers__lookup__PronunciationResponse'];
export type EtymologyResponse = components['schemas']['EtymologyResponse'];
export type ModelInfoResponse = components['schemas']['ModelInfoResponse'];
export type AudioFileResponse = components['schemas']['AudioFileResponse'];
export type ImageResponse = components['schemas']['ImageResponse'];
export type ExampleResponse = components['schemas']['floridify__api__routers__lookup__ExampleResponse'];

// ── Definition sub-models ───────────────────────────────────────────

export type WordFormResponse = components['schemas']['WordFormResponse'];
export type MeaningClusterResponse = components['schemas']['MeaningClusterResponse'];
export type UsageNoteResponse = components['schemas']['UsageNoteResponse'];
export type GrammarPatternResponse = components['schemas']['GrammarPatternResponse'];
export type CollocationResponse = components['schemas']['CollocationResponse'];

// ── Search types ────────────────────────────────────────────────────
// SearchResponse is kept in responses.ts — the generated version types
// `results` as `unknown[]` which is too weak for consumer use.
//
// NOTE: The /search router is excluded from OpenAPI when deployed with
// SEARCH_SERVICE_URL (search runs as a separate microservice). The types
// below are kept as local fallbacks isomorphic with backend
// `floridify.search.constants` and `floridify.api.routers.search` models.
// Sync manually when those backend models change.

export type SearchMode = 'smart' | 'exact' | 'fuzzy' | 'semantic';
export const SearchMode = {
    SMART: 'smart',
    EXACT: 'exact',
    FUZZY: 'fuzzy',
    SEMANTIC: 'semantic',
} as const satisfies Record<string, SearchMode>;

export interface SemanticStatusResponse {
    ready: boolean;
    enabled: boolean;
    building: boolean;
    message?: string | null;
    initialized?: boolean;
    model_name?: string | null;
    vocabulary_size?: number;
    embedding_dimension?: number | null;
    index_type?: string | null;
    backend?: string | null;
    last_built_at?: string | null;
    error?: string | null;
}

export interface HotReloadStatusResponse {
    enabled: boolean;
    polling_interval_seconds: number;
    last_check_at: string | null;
    last_reload_at: string | null;
    current_vocabulary_hash: string | null;
}

export interface RebuildIndexRequest {
    corpus_name?: string;
    corpus_uuid?: string;
    languages?: string[];
    components?: string[];
    clear_caches?: boolean;
    clean_gridfs?: boolean;
}

export interface RebuildIndexResponse {
    status: string;
    message: string;
    corpus_name: string;
    corpus_uuid?: string;
    components_rebuilt: string[];
    vocabulary_size: number;
    caches_cleared: Record<string, number>;
    gridfs_cleaned: number;
    total_time_seconds: number;
    semantic_info: Record<string, unknown>;
}

// ── Version types ───────────────────────────────────────────────────

export type VersionSummary = components['schemas']['VersionSummary-Output'];
export type FieldChangeSummary = components['schemas']['FieldChangeSummary'];
export type EditMetadataSummary = components['schemas']['EditMetadataSummary'];
export type VersionHistoryResponse = components['schemas']['VersionHistoryResponse'];
export type VersionDiffResponse = components['schemas']['VersionDiffResponse'];

// ── Corpus types ────────────────────────────────────────────────────

export type CorpusResponse = components['schemas']['CorpusResponse'];

// ── Wordlist types ──────────────────────────────────────────────────

export type WordListEntryInput = components['schemas']['WordListEntryInput'];
export type WordListCreate = components['schemas']['WordListCreate'];
export type WordListUpdate = components['schemas']['WordListUpdate'];

// Response shapes — generated from backend Pydantic models. The frontend
// `WordListResponse` is metadata-only; items are loaded via /words endpoint.
export type WordListResponse = components['schemas']['WordListResponse'];
export type WordListItemResponse = components['schemas']['WordListItemResponse-Output'];

// Sub-models referenced by the responses above
export type LearningStats = components['schemas']['LearningStats'];
export type ReviewData = components['schemas']['ReviewData-Output'];
export type ReviewHistoryItem = components['schemas']['ReviewHistoryItem'];

// Enum-like unions — runtime-accessible via the const objects below
export type MasteryLevel = components['schemas']['MasteryLevel'];
export const MasteryLevel = {
    DEFAULT: 'default',
    BRONZE: 'bronze',
    SILVER: 'silver',
    GOLD: 'gold',
} as const satisfies Record<string, MasteryLevel>;

export type Temperature = components['schemas']['Temperature'];
export const Temperature = {
    HOT: 'hot',
    COLD: 'cold',
} as const satisfies Record<string, Temperature>;

export type CardState = components['schemas']['CardState'];
export const CardState = {
    NEW: 'new',
    LEARNING: 'learning',
    YOUNG: 'young',
    MATURE: 'mature',
    RELEARNING: 'relearning',
} as const satisfies Record<string, CardState>;

// ── Source references ───────────────────────────────────────────────

export type SourceReference = components['schemas']['SourceReference'];
export type SourceVersionSpec = components['schemas']['SourceVersionSpec'];
