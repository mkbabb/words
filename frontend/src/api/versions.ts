import type {
  VersionHistoryResponse,
  VersionDetailResponse,
  VersionDiffResponse,
  RollbackResponse,
} from '@/types/api';
import { api } from './core';

export const versionsApi = {
  // List all versions of a word's synthesized entry
  async getHistory(word: string): Promise<VersionHistoryResponse> {
    const response = await api.get(`/words/${encodeURIComponent(word)}/versions`);
    return response.data;
  },

  // Get a specific version's full content
  async getVersion(word: string, version: string): Promise<VersionDetailResponse> {
    const response = await api.get(
      `/words/${encodeURIComponent(word)}/versions/${encodeURIComponent(version)}`
    );
    return response.data;
  },

  // Compute diff between two versions
  async diff(word: string, fromVersion: string, toVersion: string): Promise<VersionDiffResponse> {
    const response = await api.get(`/words/${encodeURIComponent(word)}/diff`, {
      params: { from: fromVersion, to: toVersion },
    });
    return response.data;
  },

  // Rollback to a previous version (creates new version with old content)
  async rollback(word: string, version: string): Promise<RollbackResponse> {
    const response = await api.post(`/words/${encodeURIComponent(word)}/rollback`, null, {
      params: { version },
    });
    return response.data;
  },
};
