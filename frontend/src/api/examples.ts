import { api } from './core';

export const examplesApi = {
  // Update example - PUT /examples/{id}
  async updateExample(exampleId: string, updates: { text: string }): Promise<any> {
    console.log('[API] Updating example:', exampleId, 'with:', updates);
    try {
      const response = await api.put(`/examples/${exampleId}`, updates);
      console.log('[API] Example update successful:', response.data);
      return response.data;
    } catch (error) {
      console.error('[API] Example update failed:', error);
      throw error;
    }
  },
};