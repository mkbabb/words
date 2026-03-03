import type { ResourceResponse } from '@/types/api';
import { api, API_BASE_URL } from './core';

export interface GenerateAudioParams {
  word: string;
  accent?: 'american' | 'british';
  voice_gender?: 'male' | 'female';
  language?: string; // ISO language code, defaults to "en"
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
    // External URLs (provider audio) are used directly
    if (contentUrl.startsWith('http://') || contentUrl.startsWith('https://')) {
      return contentUrl;
    }
    // Internal URLs: strip /api/v1 prefix and prepend our base URL
    return `${API_BASE_URL}${contentUrl.replace(/^\/api\/v1/, '')}`;
  },

  async generateAudio(params: GenerateAudioParams): Promise<GenerateAudioResponse> {
    const response = await api.post<ResourceResponse>('/audio/tts/generate', {
      word: params.word,
      accent: params.accent ?? 'american',
      voice_gender: params.voice_gender ?? 'male',
      language: params.language ?? 'en',
    });
    return response.data.data as GenerateAudioResponse;
  },
};
