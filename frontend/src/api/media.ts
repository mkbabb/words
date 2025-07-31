import type { ImageMedia, ResourceResponse } from '@/types/api';
import { api } from './core';

export const mediaApi = {
  // Upload image
  async uploadImage(file: File, options?: {
    alt_text?: string;
    description?: string;
  }): Promise<ImageMedia> {
    const formData = new FormData();
    formData.append('file', file);
    
    // Backend expects metadata as query parameters, not form data
    const queryParams: Record<string, string> = {};
    if (options?.alt_text) queryParams.alt_text = options.alt_text;
    if (options?.description) queryParams.description = options.description;
    
    const response = await api.post<ResourceResponse>(
      `/images`,
      formData,
      {
        params: queryParams,
        headers: {
          'Content-Type': undefined, // Explicitly remove the default JSON content-type
        },
      }
    );
    
    // Extract image data from ResourceResponse
    return {
      id: response.data.data.id,
      url: response.data.data.url,
      format: response.data.data.format,
      size_bytes: response.data.data.size_bytes,
      width: response.data.data.width,
      height: response.data.data.height,
      alt_text: response.data.data.alt_text,
      description: response.data.data.description,
      created_at: response.data.data.created_at,
      updated_at: response.data.data.updated_at,
      version: response.data.data.version || 1,
    };
  },

  // Get image metadata
  async getImage(imageId: string): Promise<ImageMedia> {
    const response = await api.get(`/images/${imageId}`);
    return response.data;
  },

  // Update image metadata
  async updateImage(imageId: string, updates: {
    alt_text?: string;
    description?: string;
  }): Promise<ImageMedia> {
    const response = await api.put<ResourceResponse>(`/images/${imageId}`, updates);
    return response.data.data;
  },

  // Delete image
  async deleteImage(imageId: string): Promise<void> {
    await api.delete(`/images/${imageId}`);
  },

  // Bind image to definition
  async bindImageToDefinition(definitionId: string, imageId: string): Promise<any> {
    const response = await api.patch(`/definitions/${definitionId}`, {
      add_image_id: imageId
    });
    return response.data;
  },

  // Remove image from definition
  async removeImageFromDefinition(definitionId: string, imageId: string): Promise<any> {
    const response = await api.patch(`/definitions/${definitionId}`, {
      remove_image_id: imageId
    });
    return response.data;
  }
};