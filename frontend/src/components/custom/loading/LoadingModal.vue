<template>
    <Modal v-model="modelValue" :close-on-backdrop="allowDismiss">
        <div class="flex flex-col items-center space-y-6 px-4">
            <AnimatedText
                :text="word"
                text-class="text-6xl lg:text-8xl font-black pb-8"
                :offset="0.15"
                :show-dots="progress < 100"
                :force-single-line="true"
            />

            <!-- Progress Component -->
            <LoadingProgress
                :progress="progress"
                :interactive="allowDismiss"
                :current-stage="currentStage"
                :stage-message="currentStageText"
                @progress-change="$emit('progress-change', $event)"
            />

            <!-- Stage Description Text -->
            <div class="max-w-md text-center">
                <ShimmerText
                    :text="currentStageText"
                    text-class="text-xl font-semibold italic text-gray-800 dark:text-gray-100"
                    :class="progressTextClass"
                    :duration="3200"
                />
            </div>

        </div>
    </Modal>
</template>

<script setup lang="ts">
import { computed, watch } from 'vue';
import { Modal } from '@/components/custom';
import { AnimatedText, ShimmerText } from '@/components/custom/animation';
import { LoadingProgress } from '@/components/custom/loading';


interface Props {
    modelValue: boolean;
    word: string;
    progress: number;
    currentStage: string;
    allowDismiss?: boolean;
}

interface Emits {
    (e: 'update:modelValue', value: boolean): void;
    (e: 'progress-change', progress: number): void;
}

const props = withDefaults(defineProps<Props>(), {
    allowDismiss: false,
});

const emit = defineEmits<Emits>();

// Debug props
watch(
    () => props.progress,
    (newVal) => {
        console.log('LoadingModal progress prop:', newVal);
    }
);

watch(
    () => props.modelValue,
    (newVal) => {
        console.log('LoadingModal visible:', newVal);
    }
);

// Computed properties

const currentStageText = computed(() => {
    // Handle undefined or empty stage
    if (!props.currentStage) {
        return 'Initializing...';
    }

    const stageMessages: Record<string, string> = {
        // Main pipeline stages (uppercase from backend)
        START: 'Initializing lookup pipeline...',
        SEARCH_START: 'Beginning word search...',
        SEARCH_COMPLETE: 'Search results found...',
        PROVIDER_FETCH_START: 'Fetching from dictionary providers...',
        PROVIDER_FETCH_COMPLETE: 'Provider data collected...',
        AI_CLUSTERING: 'Clustering definitions by meaning...',
        AI_SYNTHESIS: 'AI synthesizing comprehensive definitions...',
        AI_FALLBACK: 'Using AI fallback for definitions...',
        STORAGE_SAVE: 'Saving to knowledge base...',
        COMPLETE: 'Lookup complete!',
        complete: 'Lookup complete!', // Handle both cases
        
        // Provider-specific HTTP stages
        PROVIDER_FETCH_HTTP_CONNECTING: 'Connecting to dictionary APIs...',
        PROVIDER_FETCH_HTTP_DOWNLOADING: 'Downloading dictionary data...',
        PROVIDER_FETCH_HTTP_RATE_LIMITED: 'Rate limited - waiting...',
        PROVIDER_FETCH_HTTP_PARSING: 'Parsing provider responses...',
        PROVIDER_FETCH_HTTP_COMPLETE: 'Provider fetch complete...',
        PROVIDER_FETCH_ERROR: 'Provider error - retrying...',
        
        // Error state
        error: 'An error occurred',
    };

    // Return the mapped message if available, otherwise use the stage itself as a readable message
    const mappedMessage = stageMessages[props.currentStage];
    if (mappedMessage) {
        return mappedMessage;
    }
    
    // If no mapping exists, convert the stage to a readable format
    // Convert UPPERCASE_STAGE to "Uppercase stage..."
    const readableStage = props.currentStage
        .toLowerCase()
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (char) => char.toUpperCase());
    
    return `${readableStage}...`;
});

const progressTextClass = computed(() => ({
    'animate-pulse': props.progress < 100,
    'text-green-600 dark:text-green-400': props.progress >= 100,
}));

// Pass through the model value
const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});
</script>

<style scoped>
@keyframes fade-in {
    from {
        opacity: 0;
        transform: translateY(10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-fade-in {
    animation: fade-in 0.5s ease-out forwards;
    opacity: 0;
}
</style>
