import { api } from './core';
import type { UserProfile, UserPreferences, UserHistoryData, UserRole } from '@/types/api';
import type { LearningStats } from '@/types/wordlist';

/** Aggregated learning stats response from GET /users/me/learning-stats */
export interface GlobalLearningStatsResponse {
  global: LearningStats;
  per_wordlist: Array<{
    wordlist_id: string;
    name: string;
    unique_words: number;
    total_words: number;
    learning_stats: LearningStats;
  }>;
}

export const usersApi = {
  /** Get the current user's profile */
  async getProfile(): Promise<UserProfile> {
    const { data } = await api.get<UserProfile>('/users/me');
    return data;
  },

  /** Update the current user's profile */
  async updateProfile(fields: { username?: string; avatar_url?: string }): Promise<UserProfile> {
    const { data } = await api.patch<UserProfile>('/users/me', fields);
    return data;
  },

  /** Get the current user's preferences */
  async getPreferences(): Promise<UserPreferences> {
    const { data } = await api.get<UserPreferences>('/users/me/preferences');
    return data;
  },

  /** Set the current user's preferences (full replacement) */
  async updatePreferences(preferences: UserPreferences): Promise<UserPreferences> {
    const { data } = await api.put<UserPreferences>('/users/me/preferences', { preferences });
    return data;
  },

  /** Get the current user's history */
  async getHistory(): Promise<UserHistoryData> {
    const { data } = await api.get<UserHistoryData>('/users/me/history');
    return data;
  },

  /** Sync history from frontend to backend */
  async syncHistory(history: {
    search_history: Array<Record<string, any>>;
    lookup_history: Array<Record<string, any>>;
  }): Promise<UserHistoryData> {
    const { data } = await api.post<UserHistoryData>('/users/me/history/sync', history);
    return data;
  },

  /** Get aggregated global learning stats across all wordlists */
  async getLearningStats(): Promise<GlobalLearningStatsResponse> {
    const { data } = await api.get<GlobalLearningStatsResponse>('/users/me/learning-stats');
    return data;
  },

  // --- Admin endpoints ---

  /** List all users (admin only) */
  async listUsers(skip = 0, limit = 50): Promise<UserProfile[]> {
    const { data } = await api.get<UserProfile[]>('/users', { params: { skip, limit } });
    return data;
  },

  /** Update a user's role (admin only) */
  async updateRole(clerkId: string, role: UserRole): Promise<UserProfile> {
    const { data } = await api.patch<UserProfile>(`/users/${clerkId}/role`, { role });
    return data;
  },
};
