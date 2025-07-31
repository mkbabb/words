import type { HealthResponse } from '@/types/api';
import { api, transformError } from './core';

export const healthApi = {
  // Health check with proper response type
  async healthCheck(): Promise<HealthResponse> {
    try {
      const response = await api.get<HealthResponse>('/health');
      return response.data;
    } catch (error) {
      throw transformError(error);
    }
  },
};