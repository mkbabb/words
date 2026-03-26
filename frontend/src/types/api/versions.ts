/**
 * Frontend-only version/diff types.
 *
 * Types with backend equivalents (VersionSummary, FieldChangeSummary,
 * EditMetadataSummary, VersionHistoryResponse, VersionDiffResponse) are
 * now in schemas.ts (generated from OpenAPI).
 */

// Frontend-only types (no generated equivalent)

export interface SynthesisAuditSummary {
    model_name: string;
    model_tier?: string;
    components_enhanced: string[];
    total_tokens?: number;
    response_time_ms?: number;
    source_providers: string[];
    definitions_input: number;
    definitions_output: number;
    dedup_removed: number;
    clusters_created: number;
}

export type OperationType =
    | 'ai_synthesis'
    | 'manual_edit'
    | 'provider_refresh'
    | 'rollback'
    | 'component_regeneration'
    | 'auto_correct'
    | 'import';

export interface VersionDetailResponse {
    resource_id: string;
    version: string;
    created_at: string;
    data_hash: string;
    storage_mode: string;
    is_latest: boolean;
    content: Record<string, any>;
}

export interface RollbackResponse {
    status: 'rolled_back';
    resource_id: string;
    restored_from_version: string;
    new_version: string;
    created_at: string;
}
