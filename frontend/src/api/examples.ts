import type { Example } from '@/types/api';
import { api, transformError } from './core';
import { logger } from '@/utils/logger';

export const examplesApi = {
  // Update example - PUT /examples/{id}
  async updateExample(exampleId: string, updates: { text: string }): Promise<Example> {
    try {
      const response = await api.put<Example>(`/examples/${exampleId}`, updates);
      return response.data;
    } catch (error) {
      logger.error('Example update failed:', error);
      throw transformError(error);
    }
  },
};