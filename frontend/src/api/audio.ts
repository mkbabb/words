import type { ResourceResponse } from '@/types/api';
import { api, API_BASE_URL } from './core';

export interface GenerateAudioParams {
  word: string;
  accent?: 'american' | 'british';
  voice_gender?: 'male' | 'female';
}

export interface GenerateAudioResponse {
  id: string;
  url: string;
  format: string;
  size_bytes: number;
  duration_ms: number;
  accent: string;
  quality: string;
  content_url: string;
}

export const audioApi = {
  getAudioContentUrl(contentUrl: string): string {
    return `${API_BASE_URL}${contentUrl.replace(/^\/api\/v1/, '')}`;
  },

  async generateAudio(params: GenerateAudioParams): Promise<GenerateAudioResponse> {
    const response = await api.post<ResourceResponse>('/audio/tts/generate', {
      word: params.word,
      accent: params.accent ?? 'american',
      voice_gender: params.voice_gender ?? 'male',
    });
    return response.data.data as GenerateAudioResponse;
  },
};
