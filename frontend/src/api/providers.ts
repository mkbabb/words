import { api } from './core';

export interface ProviderEntry {
  provider: string;
  id: string;
  etymology: { text: string; language?: string; period?: string } | null;
  model_info: Record<string, any> | null;
  definitions: Array<{
    id: string;
    part_of_speech: string;
    text: string;
    synonyms: string[];
    antonyms: string[];
    examples: Array<{ text: string; source?: string }>;
  }>;
  richness_score?: number;
  definition_count?: number;
  fetched_at?: string;
}

export const providersApi = {
  /** Get all provider entries for a word */
  async getWordProviders(word: string): Promise<ProviderEntry[]> {
    const { data } = await api.get<ProviderEntry[]>(`/lookup/${encodeURIComponent(word)}/providers`);
    return data;
  },
};
