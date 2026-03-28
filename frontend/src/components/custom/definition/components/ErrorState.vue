<template>
    <div
        class="flex min-h-[400px] flex-col items-center justify-center px-6 text-center"
    >
        <div class="mb-6">
            <div class="relative mb-4 inline-flex items-center justify-center">
                <img
                    :src="errorImage"
                    :alt="errorAlt"
                    class="h-20 w-20 object-contain"
                    :class="errorImageClass"
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

        <div class="flex items-center gap-3">
            <Button
                v-if="retryable"
                @click="$emit('retry')"
                variant="default"
                size="sm"
                class="min-w-[80px]"
            >
                <RotateCcw :size="16" class="mr-2" />
                Try Again
            </Button>

            <Button
                v-if="showHelp"
                @click="$emit('help')"
                variant="outline"
                size="sm"
            >
                <HelpCircle :size="16" class="mr-2" />
                Get Help
            </Button>
        </div>

        <!-- Optional additional content slot -->
        <div v-if="$slots.default" class="mt-6">
            <slot />
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Button } from '@mkbabb/glass-ui';
import { RotateCcw, HelpCircle } from 'lucide-vue-next';
import swirlIcon from '@/assets/yoshi/ui/swirl_icon.png';
import sunIcon from '@/assets/yoshi/ui/sun_icon.png';
import heartBubble3 from '@/assets/yoshi/ui/heart_speech_bubble_3.png';

interface ErrorStateProps {
    title?: string;
    message?: string;
    errorType?:
        | 'network'
        | 'not-found'
        | 'server'
        | 'ai-failed'
        | 'empty'
        | 'unknown';
    retryable?: boolean;
    showHelp?: boolean;
}

const props = withDefaults(defineProps<ErrorStateProps>(), {
    title: 'Something went wrong',
    message: 'An unexpected error occurred. Please try again.',
    errorType: 'unknown',
    retryable: true,
    showHelp: false,
});

defineEmits<{
    retry: [];
    help: [];
}>();

const errorImage = computed(() => {
    switch (props.errorType) {
        case 'network':
        case 'server':
            return swirlIcon;
        case 'not-found':
        case 'empty':
            return sunIcon;
        case 'ai-failed':
        default:
            return heartBubble3;
    }
});

const errorAlt = computed(() => {
    switch (props.errorType) {
        case 'network':
        case 'server':
            return 'Connection error';
        case 'not-found':
        case 'empty':
            return 'Not found';
        case 'ai-failed':
        default:
            return 'Something went wrong';
    }
});

const errorImageClass = computed(() => {
    switch (props.errorType) {
        case 'network':
        case 'server':
            // Swirl: gentle spin animation for "confused/disconnected" feel
            return 'opacity-70 animate-[spin_8s_linear_infinite]';
        case 'not-found':
        case 'empty':
            // Sun: subtle pulse for "wilting" feel
            return 'opacity-50 animate-pulse';
        case 'ai-failed':
        default:
            // Heart: static but slightly transparent
            return 'opacity-60';
    }
});
</script>
