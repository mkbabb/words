import type { ResourceResponse } from '@/types/api';
import { api, transformError } from './core';

export const definitionsApi = {
  // Get definition by ID - GET /definitions/{id}
  async getDefinition(definitionId: string): Promise<any> {
    const response = await api.get(`/definitions/${definitionId}`);
    return response.data.data;
  },

  // Update definition - PUT /definitions/{id}
  async updateDefinition(definitionId: string, updates: Partial<{
    text: string;
    part_of_speech: string;
    synonyms: string[];
    antonyms: string[];
    language_register: string;
    domain: string;
    region: string;
    cefr_level: string;
    frequency_band: number;
  }>): Promise<ResourceResponse> {
    console.log('[API] Updating definition:', definitionId, 'with:', updates);
    try {
      const response = await api.put<ResourceResponse>(`/definitions/${definitionId}`, updates);
      console.log('[API] Update successful:', response.data);
      return response.data;
    } catch (error) {
      console.error('[API] Update failed:', error);
      throw transformError(error);
    }
  },

  // Regenerate definition components - POST /definitions/{id}/regenerate
  async regenerateComponents(definitionId: string, component: string): Promise<any> {
    const response = await api.post(`/definitions/${definitionId}/regenerate`, {
      components: [component],
      force: true
    });
    return response.data.data;
  },
};