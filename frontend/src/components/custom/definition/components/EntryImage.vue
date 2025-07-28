<template>
    <div v-if="image" class="absolute top-2 right-2 sm:top-4 sm:right-4 z-10">
        <HoverCard v-if="image.description">
            <HoverCardTrigger as-child>
                <img 
                    :src="image.url"
                    :alt="image.alt_text || fallbackText"
                    class="w-32 h-32 sm:w-40 sm:h-40 md:w-48 md:h-48 object-contain transition-transform duration-300 hover:scale-105 cursor-pointer"
                    @error="handleImageError"
                    @click="handleImageClick"
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
            class="w-32 h-32 sm:w-40 sm:h-40 md:w-48 md:h-48 object-contain transition-transform duration-300 hover:scale-105 cursor-pointer"
            @error="handleImageError"
            @click="handleImageClick"
        />
    </div>
</template>

<script setup lang="ts">
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import type { ImageMedia } from '@/types/api';

interface EntryImageProps {
    image: ImageMedia | null;
    fallbackText: string;
}

defineProps<EntryImageProps>();

const emit = defineEmits<{
    'image-error': [event: Event];
    'image-click': [];
}>();

const handleImageError = (event: Event) => {
    console.error('Failed to load image:', (event.target as HTMLImageElement).src);
    // Hide the image on error
    (event.target as HTMLImageElement).style.display = 'none';
    emit('image-error', event);
};

const handleImageClick = () => {
    emit('image-click');
};
</script>