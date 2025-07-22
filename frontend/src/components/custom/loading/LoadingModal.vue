<template>
    <Modal v-model="modelValue" :close-on-backdrop="allowDismiss">
        <div class="flex flex-col items-center space-y-6 px-4">
            <!-- Animated Text with Stage Lighting -->
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

            <!-- AI Facts Section -->
            <div
                v-if="facts.length > 0"
                class="w-full max-w-2xl space-y-4"
                :class="[
                    'ease-apple-bounce transition-all duration-500',
                    'transform',
                    facts.length > 0
                        ? 'translate-y-0 opacity-100'
                        : 'translate-y-4 opacity-0',
                ]"
            >
                <h3 class="text-left text-lg font-medium text-foreground/80">
                    Interesting Facts
                </h3>

                <!-- Gradient Divider -->
                <div class="relative h-px w-full overflow-hidden">
                    <div
                        class="absolute inset-0 bg-gradient-to-r
                            from-transparent via-primary/30 to-transparent"
                    />
                </div>

                <div class="space-y-4 p-2">
                    <div
                        v-for="(fact, index) in facts"
                        :key="index"
                        class="themed-card mx-2 rounded-xl border-2
                            border-border/50 p-5"
                        :class="[
                            'bg-background/80 backdrop-blur-md',
                            'cartoon-shadow-sm',
                            'ease-apple-bounce transition-all duration-300',
                            'animate-fade-in',
                        ]"
                        :style="{ animationDelay: `${index * 150}ms` }"
                    >
                        <div class="border-l-2 border-accent pl-4">
                            <p class="text-definition mb-2 text-foreground/90">
                                {{ fact.content }}
                            </p>
                            <div
                                v-if="
                                    fact.category && fact.category !== 'general'
                                "
                                class="mt-3 inline-block"
                            >
                                <span
                                    class="themed-word-type rounded-full px-2.5
                                        py-1 text-xs font-medium"
                                >
                                    {{ fact.category }}
                                </span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </Modal>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Modal } from '@/components/custom';
import { AnimatedText, ShimmerText } from '@/components/custom/animation';
import { LoadingProgress } from '@/components/custom/loading';

interface Fact {
    content: string;
    category: string;
    confidence: number;
}

interface Props {
    modelValue: boolean;
    word: string;
    progress: number;
    currentStage: string;
    facts?: Fact[];
    allowDismiss?: boolean;
}

interface Emits {
    (e: 'update:modelValue', value: boolean): void;
    (e: 'progress-change', progress: number): void;
}

const props = withDefaults(defineProps<Props>(), {
    facts: () => [],
    allowDismiss: false,
});

const emit = defineEmits<Emits>();

// Computed properties

const currentStageText = computed(() => {
    // Handle undefined or empty stage
    if (!props.currentStage) {
        return 'Processing...';
    }

    const stageMessages: Record<string, string> = {
        // Main pipeline stages
        initialization: 'Initializing search...',
        search: 'Searching through dictionaries...',
        provider_fetch: 'Gathering definitions...',
        ai_clustering: 'Analyzing meaning patterns...',
        ai_synthesis: 'Synthesizing comprehensive definitions...',
        ai_examples: 'Generating modern usage examples...',
        ai_synonyms: 'Finding beautiful synonyms...',
        storage_save: 'Saving to knowledge base...',
        complete: 'Ready!',
        error: 'An error occurred',

        // Provider sub-stages
        provider_start: 'Connecting to dictionary providers...',
        provider_connected: 'Connected to providers...',
        provider_downloading: 'Downloading definitions...',
        provider_parsing: 'Parsing dictionary data...',
        provider_complete: 'Provider data ready...',

        // Search sub-stages
        search_exact: 'Searching for exact matches...',
        search_fuzzy: 'Trying fuzzy search...',
        search_semantic: 'Performing semantic search...',
        search_prefix: 'Searching by prefix...',
    };

    return stageMessages[props.currentStage] || 'Processing...';
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
