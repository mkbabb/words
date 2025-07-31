import type { VocabularySuggestionsResponse } from '@/types';
import { api } from './core';

export const suggestionsApi = {
  // Get vocabulary suggestions - GET /suggestions or POST /suggestions
  async getVocabulary(
    words?: string[]
  ): Promise<VocabularySuggestionsResponse> {
    // Use GET when no words (empty array), POST when words provided
    if (!words || words.length === 0) {
      const response = await api.get(`/suggestions`, {
        params: { count: 10 },
      });
      return response.data;
    } else {
      const response = await api.post(`/suggestions`, {
        words: words.slice(0, 10), // Take last 10 words max
        count: 10,
      });
      return response.data;
    }
  },
};