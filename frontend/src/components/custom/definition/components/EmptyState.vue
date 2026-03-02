<template>
    <div
        class="flex min-h-[400px] flex-col items-center justify-center px-6 text-center"
    >
        <div class="mb-6">
            <div class="relative mb-4 inline-flex items-center justify-center">
                <img
                    :src="heartBubble"
                    alt="Yoshi heart speech bubble"
                    class="h-20 w-20 object-contain opacity-60"
                    draggable="false"
                />
            </div>
        </div>

        <h3 class="mb-2 text-xl font-semibold text-foreground">
            {{ title }}
        </h3>

        <p class="mb-6 max-w-md leading-relaxed text-muted-foreground">
            {{ message }}
        </p>

        <!-- Action buttons slot -->
        <div
            v-if="$slots.actions || showSuggestions"
            class="flex items-center gap-3"
        >
            <slot name="actions" />

            <Button
                v-if="showSuggestions"
                @click="$emit('suggest-alternatives')"
                variant="default"
                size="sm"
            >
                <Lightbulb :size="16" class="mr-2" />
                Suggest alternatives
            </Button>
        </div>

        <!-- Optional additional content -->
        <div v-if="$slots.default" class="mt-6">
            <slot />
        </div>
    </div>
</template>

<script setup lang="ts">
import { Button } from '@/components/ui/button';
import { Lightbulb } from 'lucide-vue-next';
import heartBubble from '@/assets/yoshi/ui/heart_speech_bubble.png';

interface EmptyStateProps {
    title?: string;
    message?: string;
    emptyType?: 'no-results' | 'no-definitions' | 'no-suggestions' | 'generic';
    showSuggestions?: boolean;
}

const props = withDefaults(defineProps<EmptyStateProps>(), {
    title: 'No results found',
    message: 'Try searching for a different word or check your spelling.',
    emptyType: 'no-results',
    showSuggestions: false,
});

defineEmits<{
    'suggest-alternatives': [];
}>();

void props.emptyType;
</script>
