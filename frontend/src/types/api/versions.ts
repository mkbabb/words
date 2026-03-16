/**
 * Backend API Type Definitions - Version History
 *
 * Isomorphic to backend VersionSummary, VersionHistoryResponse, VersionDiffResponse.
 */

export interface FieldChangeSummary {
    field_path: string;
    change_type: 'added' | 'removed' | 'modified';
    old_value: string | null;
    new_value: string | null;
}

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

export interface EditMetadataSummary {
    user_id?: string;
    username?: string;
    operation_type: OperationType;
    change_reason?: string;
    field_changes: FieldChangeSummary[];
    synthesis_audit?: SynthesisAuditSummary;
}

export interface VersionSummary {
    version: string;
    created_at: string;
    data_hash: string;
    storage_mode: 'snapshot' | 'delta';
    is_latest: boolean;
    edit_metadata?: EditMetadataSummary;
}

export interface VersionHistoryResponse {
    resource_id: string;
    total_versions: number;
    versions: VersionSummary[];
    timestamp: string;
    version: string;
}

export interface VersionDiffResponse {
    from_version: string;
    to_version: string;
    changes: Record<string, any>;
    timestamp: string;
    version: string;
}

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
