import { api } from './core';
import { logger } from '@/utils/logger';

export const examplesApi = {
  // Update example - PUT /examples/{id}
  async updateExample(exampleId: string, updates: { text: string }): Promise<any> {
    try {
      const response = await api.put(`/examples/${exampleId}`, updates);
      return response.data;
    } catch (error) {
      logger.error('Example update failed:', error);
      throw error;
    }
  },
};