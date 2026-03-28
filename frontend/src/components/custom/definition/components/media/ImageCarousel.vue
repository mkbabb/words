<template>
    <div
        v-if="(images && images.length > 0) || editMode"
        class="absolute top-2 right-2 z-content sm:top-4 sm:right-4"
    >
        <div class="group relative" @mouseenter="handleMouseEnter">
            <Carousel
                v-slot="{ canScrollNext, canScrollPrev }"
                class="w-32 max-w-xs sm:w-40 md:w-48"
                :opts="{
                    align: 'center',
                    loop: true,
                    skipSnaps: false,
                    dragFree: false,
                }"
                @init-api="onCarouselInit"
            >
                <CarouselContent class="-ml-1">
                    <!-- Regular image items -->
                    <CarouselItem
                        v-for="(image, index) in images"
                        :key="image.id"
                        class="pl-1"
                    >
                        <CarouselSlide
                            :image="image"
                            :index="index"
                            :fallback-text="fallbackText"
                            :edit-mode="editMode"
                            :deleting="deletingImages.has(image.id)"
                            :should-load="shouldLoadImage(index)"
                            :loaded="isImageLoaded(index)"
                            @delete="handleDeleteImage"
                            @load="onImageLoad"
                            @error="handleImageError"
                        />
                    </CarouselItem>
                </CarouselContent>

                <!-- Navigation Controls (show when there are scrollable items) -->
                <template v-if="totalCarouselItems > 1">
                    <CarouselPrevious
                        v-show="showControls"
                        class="absolute top-1/2 left-1 h-8 w-8 -translate-y-1/2 border-none glass-overlay transition-normal hover:scale-110 hover:bg-black/70"
                        :class="{
                            'opacity-0 group-hover:opacity-100': !showControls,
                        }"
                        @mouseenter="showControls = true"
                        @mouseleave="scheduleHideControls"
                        :disabled="!canScrollPrev"
                    />
                    <CarouselNext
                        v-show="showControls"
                        class="absolute top-1/2 right-1 h-8 w-8 -translate-y-1/2 border-none glass-overlay transition-normal hover:scale-110 hover:bg-black/70"
                        :class="{
                            'opacity-0 group-hover:opacity-100': !showControls,
                        }"
                        @mouseenter="showControls = true"
                        @mouseleave="scheduleHideControls"
                        :disabled="!canScrollNext"
                    />

                    <!-- Image Counter -->
                    <div
                        v-show="showControls"
                        class="absolute bottom-1 left-1/2 -translate-x-1/2 rounded-full glass-overlay px-2 py-1 text-xs text-white transition-normal"
                        :class="{
                            'opacity-0 group-hover:opacity-100': !showControls,
                        }"
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
import {
    Carousel,
    CarouselContent,
    CarouselItem,
    CarouselNext,
    CarouselPrevious,
} from '@mkbabb/glass-ui';
import type { CarouselApi } from '@mkbabb/glass-ui';
import CarouselSlide from './CarouselSlide.vue';
import { logger } from '@/utils/logger';
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
    return props.images?.length || 0;
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

    const currentImageIndex = currentIndex.value;

    const buffer = 1; // Load 1 image before and after current
    const start = Math.max(0, currentImageIndex - buffer);
    const end = Math.min(
        props.images.length - 1,
        currentImageIndex + buffer + 1
    );

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
    logger.error(
        'Failed to load image:',
        (event.target as HTMLImageElement).src
    );
    loadingImages.value.delete(index);
    emit('image-error', event, index);
};

// handleImageClick removed - not used in template


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
        logger.error('Failed to delete image:', error);
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
watch(
    () => props.images,
    () => {
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
    },
    { immediate: true }
);

// Watch for changes in total carousel items to refresh controls
watch(totalCarouselItems, (newCount, oldCount) => {
    if (newCount !== oldCount && carouselApi.value) {
        nextTick(() => {
            carouselApi.value?.reInit();
        });
    }
});

// Preload first image immediately
watch(
    () => props.images,
    (newImages) => {
        if (newImages && newImages.length > 0) {
            // Immediately start loading the first image
            visibleRange.value = {
                start: 0,
                end: Math.min(1, newImages.length - 1),
            };
        }
    },
    { immediate: true }
);

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

