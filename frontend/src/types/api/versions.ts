/**
 * Backend API Type Definitions - Version History
 *
 * Isomorphic to backend VersionSummary, VersionHistoryResponse, VersionDiffResponse.
 */

export interface VersionSummary {
    version: string;
    created_at: string;
    data_hash: string;
    storage_mode: 'snapshot' | 'delta';
    is_latest: boolean;
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
