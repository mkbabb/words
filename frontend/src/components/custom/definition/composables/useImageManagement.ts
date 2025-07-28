import { computed, type ComputedRef } from 'vue';
import type { SynthesizedDictionaryEntry, ImageMedia } from '@/types/api';

/**
 * Composable for managing images from synthesized dictionary entries
 * Abstracts the logic for collecting and processing images from different sources
 */
export function useImageManagement(entry: ComputedRef<SynthesizedDictionaryEntry | null>) {
    /**
     * Collects all images from the entry, prioritizing synth entry images
     * then falling back to definition images
     */
    const allImages = computed<ImageMedia[] | null>(() => {
        if (!entry.value) return null;
        
        const images: ImageMedia[] = [];
        
        // First add synth entry images (highest priority)
        if (entry.value.images && entry.value.images.length > 0) {
            for (const image of entry.value.images) {
                if (image.id) {
                    images.push({
                        ...image,
                        url: `/api/v1/images/${image.id}/content`
                    });
                }
            }
        }
        
        // Then add definition images (if no synth entry images exist)
        if (images.length === 0 && entry.value.definitions) {
            for (const def of entry.value.definitions) {
                if (def.images && def.images.length > 0) {
                    for (const image of def.images) {
                        if (image.id) {
                            images.push({
                                ...image,
                                url: `/api/v1/images/${image.id}/content`
                            });
                        }
                    }
                    break; // Only take images from first definition that has them
                }
            }
        }
        
        return images.length > 0 ? images : null;
    });

    /**
     * Gets the primary image (first available image with description preference)
     */
    const primaryImage = computed<ImageMedia | null>(() => {
        if (!allImages.value || allImages.value.length === 0) return null;
        
        // Prefer images with descriptions
        const imageWithDescription = allImages.value.find(img => img.description);
        return imageWithDescription || allImages.value[0];
    });

    /**
     * Checks if the entry has any images
     */
    const hasImages = computed<boolean>(() => {
        return allImages.value !== null && allImages.value.length > 0;
    });

    /**
     * Gets the total number of images
     */
    const imageCount = computed<number>(() => {
        return allImages.value?.length || 0;
    });

    /**
     * Helper to handle image click events
     */
    const handleImageClick = (image: ImageMedia, index?: number) => {
        if (image?.url) {
            window.open(image.url, '_blank');
        }
    };

    /**
     * Helper to handle image error events
     */
    const handleImageError = (event: Event, index?: number) => {
        console.error('Failed to load image:', (event.target as HTMLImageElement).src);
        // Hide the failed image
        (event.target as HTMLImageElement).style.display = 'none';
    };

    return {
        allImages,
        primaryImage,
        hasImages,
        imageCount,
        handleImageClick,
        handleImageError,
    };
}