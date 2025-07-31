<template>
    <div v-if="(images && images.length > 0) || editMode" class="absolute top-2 right-2 sm:top-4 sm:right-4 z-10">
        <div class="relative group" @mouseenter="handleMouseEnter">
            <Carousel
                v-slot="{ canScrollNext, canScrollPrev }"
                class="w-32 sm:w-40 md:w-48 max-w-xs"
                :opts="{
                    align: 'center',
                    loop: true,
                    skipSnaps: false,
                    dragFree: false
                }"
                @init-api="onCarouselInit"
            >
                <CarouselContent class="-ml-1">
                    <!-- Upload box as first item in edit mode -->
                    <CarouselItem 
                        v-if="editMode"
                        key="upload-box"
                        class="pl-1"
                    >
                        <div class="relative h-32 sm:h-40 md:h-48 bg-muted/10 rounded-lg overflow-hidden border-2 border-dashed border-muted-foreground/30">
                            <ImageUploader 
                                :synth-entry-id="synthEntryId"
                                class="w-full h-full"
                                size="lg"
                                variant="empty"
                                @upload-success="handleUploadSuccess"
                                @images-updated="handleImagesUpdated"
                            />
                        </div>
                    </CarouselItem>
                    
                    <!-- Regular image items -->
                    <CarouselItem 
                        v-for="(image, index) in images" 
                        :key="image.id"
                        class="pl-1"
                    >
                        <div class="relative h-32 sm:h-40 md:h-48 bg-muted/10 rounded-lg overflow-hidden group">
                            <!-- Delete button (only in edit mode) -->
                            <button
                                v-if="editMode"
                                @click="handleDeleteImage(image.id, index)"
                                :disabled="deletingImages.has(image.id)"
                                class="absolute bottom-1 right-1 z-10 w-6 h-6 bg-destructive hover:bg-destructive/80 text-destructive-foreground rounded-full flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 hover:scale-110 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                                :aria-label="`Delete image ${index + 1}`"
                            >
                                <svg v-if="!deletingImages.has(image.id)" class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                                <svg v-else class="w-3 h-3 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/>
                                </svg>
                            </button>
                            
                            <!-- Lazy Loading Implementation -->
                            <template v-if="shouldLoadImage(index)">
                                <!-- Image Loaded State -->
                                <template v-if="isImageLoaded(index)">
                                    <Transition
                                        name="image-fade"
                                        appear
                                        mode="out-in"
                                    >
                                        <HoverCard v-if="image.description">
                                            <HoverCardTrigger as-child>
                                                <img 
                                                    :src="image.url"
                                                    :alt="image.alt_text || fallbackText"
                                                    class="w-full h-full object-contain"
                                                />
                                            </HoverCardTrigger>
                                            <HoverCardContent class="w-auto px-2 py-1" side="left" :sideOffset="8">
                                                <p class="text-sm font-medium whitespace-nowrap">{{ image.description }}</p>
                                            </HoverCardContent>
                                        </HoverCard>
                                        <img 
                                            v-else
                                            :src="image.url"
                                            :alt="image.alt_text || fallbackText"
                                            class="w-full h-full object-contain"
                                        />
                                    </Transition>
                                </template>
                                
                                <!-- Image Loading State -->
                                <template v-else>
                                    <div class="absolute inset-0 bg-muted/20 animate-pulse flex items-center justify-center">
                                        <svg class="w-8 h-8 text-muted-foreground/50 animate-bounce" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 002 2z"/>
                                        </svg>
                                    </div>
                                    <!-- Hidden image for loading -->
                                    <img
                                        :src="image.url"
                                        :alt="image.alt_text || fallbackText"
                                        class="absolute inset-0 w-full h-full object-contain opacity-0"
                                        @load="() => onImageLoad(index)"
                                        @error="(e) => handleImageError(e, index)"
                                    />
                                </template>
                            </template>
                            
                            <!-- Not loaded yet (placeholder) -->
                            <template v-else>
                                <div class="absolute inset-0 bg-muted/10 flex items-center justify-center">
                                    <svg class="w-6 h-6 text-muted-foreground/40" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 002 2z"/>
                                    </svg>
                                </div>
                            </template>

                        </div>
                    </CarouselItem>
                </CarouselContent>
                
                <!-- Navigation Controls (show when there are scrollable items) -->
                <template v-if="totalCarouselItems > 1">
                    <CarouselPrevious
                        v-show="showControls"
                        class="absolute left-1 top-1/2 -translate-y-1/2 h-8 w-8 bg-black/50 border-none hover:bg-black/70 transition-all duration-300 hover:scale-110 backdrop-blur-sm hover:backdrop-blur-md"
                        :class="{ 'opacity-0 group-hover:opacity-100': !showControls }"
                        @mouseenter="showControls = true"
                        @mouseleave="scheduleHideControls"
                        :disabled="!canScrollPrev"
                    />
                    <CarouselNext
                        v-show="showControls"
                        class="absolute right-1 top-1/2 -translate-y-1/2 h-8 w-8 bg-black/50 border-none hover:bg-black/70 transition-all duration-300 hover:scale-110 backdrop-blur-sm hover:backdrop-blur-md"
                        :class="{ 'opacity-0 group-hover:opacity-100': !showControls }"
                        @mouseenter="showControls = true"
                        @mouseleave="scheduleHideControls"
                        :disabled="!canScrollNext"
                    />
                    
                    <!-- Image Counter -->
                    <div 
                        v-show="showControls"
                        class="absolute bottom-1 left-1/2 -translate-x-1/2 bg-black/50 text-white text-xs px-2 py-1 rounded-full transition-all duration-300 backdrop-blur-sm"
                        :class="{ 'opacity-0 group-hover:opacity-100': !showControls }"
                        @mouseenter="showControls = true"
                        @mouseleave="scheduleHideControls"
                    >
                        {{ currentIndex + 1 }} / {{ totalCarouselItems }}
                    </div>
                </template>
            </Carousel>
        </div>
    </div>

</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { Carousel, CarouselContent, CarouselItem, CarouselNext, CarouselPrevious } from '@/components/ui/carousel';
import type { CarouselApi } from '@/components/ui/carousel';
import ImageUploader from './ImageUploader.vue';
import type { ImageMedia } from '@/types/api';
import { mediaApi } from '@/api/media';

interface ImageCarouselProps {
    images: ImageMedia[] | null;
    fallbackText: string;
    editMode?: boolean;
    synthEntryId?: string;
}

const props = withDefaults(defineProps<ImageCarouselProps>(), {
    editMode: false,
});

const emit = defineEmits<{
    'image-error': [event: Event, imageIndex: number];
    'image-click': [image: ImageMedia, imageIndex: number];
    'images-updated': [images: ImageMedia[]];
    'image-deleted': [imageId: string];
}>();

// State
const carouselApi = ref<CarouselApi>();
const currentIndex = ref(0);
const showControls = ref(false);
const hideControlsTimeout = ref<NodeJS.Timeout | null>(null);
const deletingImages = ref(new Set<string>()); // Track images being deleted

// Computed properties
const totalCarouselItems = computed(() => {
    const imageCount = props.images?.length || 0;
    const uploadBoxCount = props.editMode ? 1 : 0;
    return imageCount + uploadBoxCount;
});

// Lazy loading state - optimize bandwidth by only loading visible + adjacent images
const loadedImages = ref(new Set<number>());
const loadingImages = ref(new Set<number>());
const visibleRange = ref({ start: 0, end: 2 }); // Load current + next 2

// Bandwidth optimization: only load images that are visible or adjacent
const shouldLoadImage = (index: number): boolean => {
    return index >= visibleRange.value.start && index <= visibleRange.value.end;
};

const isImageLoaded = (index: number): boolean => {
    return loadedImages.value.has(index);
};

// Update visible range based on current position
const updateVisibleRange = () => {
    if (!props.images || props.images.length === 0) return;
    
    // Account for upload box offset in edit mode
    const imageIndexOffset = props.editMode ? 1 : 0;
    const currentImageIndex = currentIndex.value - imageIndexOffset;
    
    // Only calculate range if we're viewing actual images (not upload box)
    if (currentImageIndex < 0) return;
    
    const buffer = 1; // Load 1 image before and after current
    const start = Math.max(0, currentImageIndex - buffer);
    const end = Math.min(props.images.length - 1, currentImageIndex + buffer + 1);
    
    visibleRange.value = { start, end };
};

// Carousel API handlers
const onCarouselInit = (api: CarouselApi) => {
    carouselApi.value = api;
    
    if (api) {
        api.on('select', () => {
            currentIndex.value = api.selectedScrollSnap();
            updateVisibleRange();
        });
        
        // Initialize
        currentIndex.value = api.selectedScrollSnap();
        updateVisibleRange();
    }
};

// Image loading handlers
const onImageLoad = (index: number) => {
    loadingImages.value.delete(index);
    loadedImages.value.add(index);
};

const handleImageError = (event: Event, index: number) => {
    console.error('Failed to load image:', (event.target as HTMLImageElement).src);
    loadingImages.value.delete(index);
    emit('image-error', event, index);
};

const handleImageClick = (image: ImageMedia, index: number) => {
    emit('image-click', image, index);
};

const handleUploadSuccess = (newImages: ImageMedia[]) => {
    emit('images-updated', newImages);
};

const handleImagesUpdated = () => {
    // Pass the event up to the parent component (DefinitionDisplay)
    // The parent will handle refreshing the synthesized entry
    emit('images-updated', []);
};

const handleDeleteImage = async (imageId: string, index: number) => {
    // Prevent duplicate deletion requests
    if (deletingImages.value.has(imageId)) {
        return;
    }
    
    try {
        // Mark image as being deleted
        deletingImages.value.add(imageId);
        
        await mediaApi.deleteImage(imageId);
        emit('image-deleted', imageId);
        
        // Remove from loaded images set
        loadedImages.value.delete(index);
        loadingImages.value.delete(index);
        
        // Adjust carousel if needed
        if (carouselApi.value && props.images && props.images.length > 1) {
            // If we deleted the last image, go to previous
            if (currentIndex.value >= props.images.length - 1) {
                carouselApi.value.scrollPrev();
            }
        }
    } catch (error) {
        console.error('Failed to delete image:', error);
        // Could emit an error event here if needed
    } finally {
        // Always remove from deleting set
        deletingImages.value.delete(imageId);
    }
};

// Control visibility
const scheduleHideControls = () => {
    if (hideControlsTimeout.value) {
        clearTimeout(hideControlsTimeout.value);
    }
    hideControlsTimeout.value = setTimeout(() => {
        showControls.value = false;
    }, 500);
};

// Mouse hover handling (used for keyboard navigation context)
const handleMouseEnter = () => {
    if (totalCarouselItems.value > 1) {
        showControls.value = true;
        if (hideControlsTimeout.value) {
            clearTimeout(hideControlsTimeout.value);
            hideControlsTimeout.value = null;
        }
    }
};

// Keyboard navigation
const handleKeydown = (event: KeyboardEvent) => {
    if (totalCarouselItems.value <= 1 || !carouselApi.value) return;
    
    switch (event.key) {
        case 'ArrowLeft':
            event.preventDefault();
            carouselApi.value.scrollPrev();
            break;
        case 'ArrowRight':
            event.preventDefault();
            carouselApi.value.scrollNext();
            break;
    }
};

// Reset loading state when images change
watch(() => props.images, () => {
    loadedImages.value.clear();
    loadingImages.value.clear();
    deletingImages.value.clear(); // Clear deletion state
    currentIndex.value = 0;
    
    if (carouselApi.value) {
        carouselApi.value.scrollTo(0);
        // Force carousel to recompute scroll state
        nextTick(() => {
            carouselApi.value?.reInit();
        });
    }
    
    nextTick(() => {
        updateVisibleRange();
    });
}, { immediate: true });

// Watch for changes in total carousel items to refresh controls
watch(totalCarouselItems, (newCount, oldCount) => {
    if (newCount !== oldCount && carouselApi.value) {
        nextTick(() => {
            carouselApi.value?.reInit();
        });
    }
});

// Preload first image immediately
watch(() => props.images, (newImages) => {
    if (newImages && newImages.length > 0) {
        // Immediately start loading the first image
        visibleRange.value = { start: 0, end: Math.min(1, newImages.length - 1) };
    }
}, { immediate: true });

// Lifecycle
onMounted(() => {
    document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
    document.removeEventListener('keydown', handleKeydown);
    if (hideControlsTimeout.value) {
        clearTimeout(hideControlsTimeout.value);
    }
});
</script>

<style scoped>
/* Image fade transitions using Tailwind utilities */
.image-fade-enter-active,
.image-fade-leave-active {
    transition: all 0.3s ease-out;
}

.image-fade-leave-active {
    transition-duration: 0.2s;
    transition-timing-function: ease-in;
}

.image-fade-enter-from {
    opacity: 0;
    transform: scale(0.95) translateY(0.5rem);
}

.image-fade-enter-to {
    opacity: 1;
    transform: scale(1) translateY(0);
}

.image-fade-leave-from {
    opacity: 1;
    transform: scale(1) translateY(0);
}

.image-fade-leave-to {
    opacity: 0;
    transform: scale(1.05) translateY(-0.25rem);
}
</style>