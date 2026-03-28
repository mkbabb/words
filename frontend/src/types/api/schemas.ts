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

// Extend the generated union with new providers until OpenAPI types are regenerated
export type DictionaryProvider = components['schemas']['DictionaryProvider']
    | 'wordnet' | 'gcide' | 'wikipedia' | 'moby_thesaurus';
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
export type SemanticStatusResponse = components['schemas']['SemanticStatusResponse'];
export type HotReloadStatusResponse = components['schemas']['HotReloadStatusResponse'];
export type RebuildIndexRequest = components['schemas']['RebuildIndexRequest'];
export type RebuildIndexResponse = components['schemas']['RebuildIndexResponse'];

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

// ── Source references ───────────────────────────────────────────────

export type SourceReference = components['schemas']['SourceReference'];
export type SourceVersionSpec = components['schemas']['SourceVersionSpec'];
