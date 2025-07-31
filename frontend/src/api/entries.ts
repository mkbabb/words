import type { ResourceResponse, SynthesizedDictionaryEntry } from '@/types/api';
import { api, transformError } from './core';

export interface EntryUpdateRequest {
  status?: string;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface ImageAddRequest {
  image_ids: string[];
}

export interface RegenerateRequest {
  components?: Set<string>;
  force?: boolean;
}

export interface FieldSelection {
  include?: string[];
  exclude?: string[];
  expand?: string[];
}

export const entriesApi = {
  // Get synthesized dictionary entry by ID - GET /words/entries/{entry_id}
  async getEntry(
    entryId: string,
    options?: FieldSelection
  ): Promise<SynthesizedDictionaryEntry> {
    try {
      const params: Record<string, any> = {};
      
      if (options?.include?.length) params.include = options.include.join(',');
      if (options?.exclude?.length) params.exclude = options.exclude.join(',');
      if (options?.expand?.length) params.expand = options.expand.join(',');
      
      const response = await api.get<ResourceResponse>(
        `/words/entries/${entryId}`,
        { params }
      );
      
      return response.data.data;
    } catch (error) {
      throw transformError(error);
    }
  },

  // Update synthesized dictionary entry - PUT /words/entries/{entry_id}
  async updateEntry(
    entryId: string, 
    updates: EntryUpdateRequest
  ): Promise<SynthesizedDictionaryEntry> {
    try {
      const response = await api.put<ResourceResponse>(
        `/words/entries/${entryId}`,
        updates
      );
      
      return response.data.data;
    } catch (error) {
      throw transformError(error);
    }
  },

  // Delete synthesized dictionary entry - DELETE /words/entries/{entry_id}
  async deleteEntry(entryId: string): Promise<boolean> {
    try {
      const response = await api.delete<ResourceResponse>(`/words/entries/${entryId}`);
      return response.data.data.deleted;
    } catch (error) {
      throw transformError(error);
    }
  },

  // Add images to synthesized dictionary entry - POST /words/entries/{entry_id}/images
  async addImagesToEntry(
    entryId: string,
    imageIds: string[]
  ): Promise<{
    entry_id: string;
    image_ids: string[];
    images_added: number;
    total_images: number;
  }> {
    try {
      const request: ImageAddRequest = { image_ids: imageIds };
      
      const response = await api.post<ResourceResponse>(
        `/words/entries/${entryId}/images`,
        request
      );
      
      return response.data.data;
    } catch (error) {
      throw transformError(error);
    }
  },

  // Remove image from synthesized dictionary entry - DELETE /words/entries/{entry_id}/images/{image_id}
  async removeImageFromEntry(
    entryId: string,
    imageId: string
  ): Promise<{
    entry_id: string;
    image_id: string;
    removed: boolean;
    remaining_images: number;
  }> {
    try {
      const response = await api.delete<ResourceResponse>(
        `/words/entries/${entryId}/images/${imageId}`
      );
      
      return response.data.data;
    } catch (error) {
      throw transformError(error);
    }
  },

  // Re-synthesize entry components - POST /words/entries/{entry_id}/regenerate
  async regenerateEntryComponents(
    entryId: string,
    options?: RegenerateRequest
  ): Promise<{
    entry_id: string;
    components: string[];
    regeneration_requested: boolean;
    status: string;
  }> {
    try {
      const request: RegenerateRequest = {
        components: options?.components || new Set(['all']),
        force: options?.force || false
      };

      const response = await api.post<ResourceResponse>(
        `/words/entries/${entryId}/regenerate`,
        request
      );
      
      return response.data.data;
    } catch (error) {
      throw transformError(error);
    }
  },

  // Utility methods for common operations
  
  // Refresh entry images (get updated entry with fresh image data)
  async refreshEntryImages(entryId: string): Promise<SynthesizedDictionaryEntry> {
    return entriesApi.getEntry(entryId, { expand: ['images'] });
  },

  // Update entry with image IDs and return updated entry
  async updateEntryWithImages(
    entryId: string, 
    imageIds: string[]
  ): Promise<SynthesizedDictionaryEntry> {
    // First add the images to the entry
    await entriesApi.addImagesToEntry(entryId, imageIds);
    
    // Then fetch the updated entry with expanded images
    return entriesApi.refreshEntryImages(entryId);
  },

  // Remove image and return updated entry
  async removeImageAndRefresh(
    entryId: string,
    imageId: string
  ): Promise<SynthesizedDictionaryEntry> {
    // Remove the image
    await entriesApi.removeImageFromEntry(entryId, imageId);
    
    // Return updated entry
    return entriesApi.refreshEntryImages(entryId);
  }
};