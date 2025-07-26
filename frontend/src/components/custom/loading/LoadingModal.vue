<template>
    <Modal v-model="modelValue" :close-on-backdrop="allowDismiss">
        <div class="flex flex-col items-center space-y-6 px-4">
            <AnimatedText
                :text="displayText || word || ''"
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
                :checkpoints="progressCheckpoints"
                :mode="mode"
                @progress-change="$emit('progress-change', $event)"
            />

            <!-- Stage Description Text -->
            <div class="max-w-md text-center space-y-2">
                <ShimmerText
                    :text="currentStageText"
                    text-class="text-xl font-semibold italic text-gray-800 dark:text-gray-100"
                    :class="progressTextClass"
                    :duration="3200"
                />
                <!-- Stage Sub-description -->
                <p class="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                    {{ stageDescription }}
                </p>
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
    word?: string;
    displayText?: string;
    progress: number;
    currentStage: string;
    allowDismiss?: boolean;
    mode?: 'lookup' | 'suggestions';
}

interface Emits {
    (e: 'update:modelValue', value: boolean): void;
    (e: 'progress-change', progress: number): void;
}

const props = withDefaults(defineProps<Props>(), {
    allowDismiss: false,
    mode: 'lookup',
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

    const lookupStageMessages: Record<string, string> = {
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
    };

    const suggestionStageMessages: Record<string, string> = {
        // AI suggestion stages
        START: 'Understanding your query...',
        QUERY_VALIDATION: 'Validating query intent...',
        WORD_GENERATION: 'Generating word suggestions...',
        SCORING: 'Evaluating word relevance...',
        COMPLETE: 'Suggestions ready!',
    };

    // Add provider-specific stages to lookup messages
    if (props.mode === 'lookup') {
        Object.assign(lookupStageMessages, {
            // Provider-specific HTTP stages
            PROVIDER_FETCH_HTTP_CONNECTING: 'Connecting to dictionary APIs...',
            PROVIDER_FETCH_HTTP_DOWNLOADING: 'Downloading dictionary data...',
            PROVIDER_FETCH_HTTP_RATE_LIMITED: 'Rate limited - waiting...',
            PROVIDER_FETCH_HTTP_PARSING: 'Parsing provider responses...',
            PROVIDER_FETCH_HTTP_COMPLETE: 'Provider fetch complete...',
            PROVIDER_FETCH_ERROR: 'Provider error - retrying...',
            
            // Error state
            error: 'An error occurred',
        });
    }

    const stageMessages = props.mode === 'suggestions' ? suggestionStageMessages : lookupStageMessages;

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

// Computed property for stage description
const stageDescription = computed(() => {
    const lookupDescriptions: Record<string, string> = {
        // Main pipeline stages
        START: 'Setting up search engines, AI models, and database connections.',
        SEARCH_START: 'Searching exact matches, fuzzy matches, and semantic similarities.',
        SEARCH_COMPLETE: 'Best match identified with confidence scoring.',
        PROVIDER_FETCH_START: 'Connecting to multiple dictionary APIs simultaneously.',
        PROVIDER_FETCH_COMPLETE: 'All available definitions have been retrieved.',
        AI_CLUSTERING: 'Grouping similar meanings to eliminate redundancy.',
        AI_SYNTHESIS: 'Creating comprehensive definitions with examples and usage notes.',
        AI_FALLBACK: 'Generating definitions from AI knowledge when sources are unavailable.',
        STORAGE_SAVE: 'Persisting results for faster future lookups.',
        COMPLETE: 'Your word is ready to explore!',
        complete: 'Your word is ready to explore!',
        
        // Provider-specific stages
        PROVIDER_FETCH_HTTP_CONNECTING: 'Establishing secure connections to dictionary services.',
        PROVIDER_FETCH_HTTP_DOWNLOADING: 'Retrieving raw definition data from providers.',
        PROVIDER_FETCH_HTTP_RATE_LIMITED: 'Respecting API limits - brief pause required.',
        PROVIDER_FETCH_HTTP_PARSING: 'Extracting structured data from provider responses.',
        PROVIDER_FETCH_HTTP_COMPLETE: 'Provider data successfully processed.',
        PROVIDER_FETCH_ERROR: 'Encountering issues - trying alternative sources.',
        
        // Error state
        error: 'Something went wrong. Please try again.',
    };

    const suggestionDescriptions: Record<string, string> = {
        // AI suggestion stages
        START: 'Analyzing your descriptive query for semantic meaning.',
        QUERY_VALIDATION: 'Ensuring your query seeks word suggestions.',
        WORD_GENERATION: 'AI is finding the perfect words to match your description.',
        SCORING: 'Ranking words by relevance and aesthetic quality.',
        COMPLETE: 'Your curated word suggestions are ready!',
    };
    
    const stageDescriptions = props.mode === 'suggestions' ? suggestionDescriptions : lookupDescriptions;
    
    return stageDescriptions[props.currentStage] || 'Processing your request...';
});

// Pass through the model value
const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

// Define different checkpoints for lookup vs suggestions
const progressCheckpoints = computed(() => {
    if (props.mode === 'suggestions') {
        return [
            { progress: 5, label: 'Start' },
            { progress: 20, label: 'Query Validation' },
            { progress: 40, label: 'Word Generation' },
            { progress: 80, label: 'Scoring' },
            { progress: 100, label: 'Complete' },
        ];
    } else {
        // Default lookup checkpoints
        return [
            { progress: 5, label: 'Start' },
            { progress: 10, label: 'Search Start' },
            { progress: 20, label: 'Search Complete' },
            { progress: 25, label: 'Provider Fetch' },
            { progress: 60, label: 'Providers Complete' },
            { progress: 70, label: 'AI Clustering' },
            { progress: 85, label: 'AI Synthesis' },
            { progress: 95, label: 'Storage' },
            { progress: 100, label: 'Complete' },
        ];
    }
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
