<template>
    <div class="flex w-full flex-col gap-1 space-y-4">
        <!-- Progress Bar -->
        <div class="relative">
            <div
                ref="progressBarRef"
                class="relative h-8 overflow-hidden rounded-full bg-gray-200
                    dark:bg-gray-700"
                :class="[
                    'shadow-inner',
                    'border border-gray-300 dark:border-gray-600',
                    interactive ? 'cursor-pointer' : '',
                ]"
                @mousedown="handleMouseDown"
                @click="handleProgressBarInteraction"
            >
                <div
                    class="h-full rounded-full transition-[width] duration-300
                        ease-out"
                    :style="{
                        width: `${normalizedProgress}%`,
                        background: rainbowGradient,
                    }"
                    :class="[
                        'shadow-lg',
                        normalizedProgress < 100 ? 'animate-pulse' : '',
                    ]"
                    :data-progress="normalizedProgress"
                />
            </div>

            <!-- Checkpoint Markers -->
            <div class="absolute top-0 bottom-0 w-full">
                <div
                    v-for="(checkpoint, index) in checkpoints"
                    :key="index"
                    class="absolute flex items-center justify-center"
                    :style="{
                        left:
                            checkpoint.progress === 0
                                ? '0%'
                                : checkpoint.progress === 100
                                  ? 'calc(100% - 16px)'
                                  : `${checkpoint.progress}%`,
                        top: '50%',
                        transform:
                            checkpoint.progress === 0 ||
                            checkpoint.progress === 100
                                ? 'translateX(-50%) translateY(-50%)'
                                : 'translateX(-50%) translateY(-50%)',
                    }"
                >
                    <HoverCard :open-delay="100" :close-delay="50">
                        <HoverCardTrigger as-child>
                            <button
                                class="h-6 w-6 rounded-full border-2
                                    transition-all duration-300 outline-none"
                                :class="[
                                    normalizedProgress >= checkpoint.progress
                                        ? 'scale-110 border-primary bg-primary'
                                        : 'border-gray-400 bg-background dark:border-gray-500',
                                    isActiveCheckpoint(checkpoint.progress)
                                        ? 'animate-pulse'
                                        : '',
                                    interactive
                                        ? 'cursor-pointer hover:scale-125'
                                        : 'cursor-help hover:scale-125',
                                ]"
                                @click="handleCheckpointClick(checkpoint)"
                                :aria-label="`${checkpoint.label} - ${checkpoint.progress}%`"
                            />
                        </HoverCardTrigger>
                        <HoverCardContent
                            class="z-[10000] w-60"
                            side="top"
                            :side-offset="16"
                            align="center"
                            :align-offset="0"
                        >
                            <div class="space-y-2">
                                <div class="flex items-center justify-between">
                                    <h4 class="text-sm font-semibold">
                                        {{ checkpoint.label }}
                                    </h4>
                                    <span
                                        class="text-xs font-medium text-primary"
                                        >{{ checkpoint.progress }}%</span
                                    >
                                </div>
                                <hr class="border-border/30" />
                                <p
                                    class="text-xs leading-relaxed
                                        text-muted-foreground"
                                >
                                    {{
                                        getCheckpointDescription(
                                            checkpoint.progress
                                        )
                                    }}
                                </p>
                                <!-- Show current stage info if this checkpoint is active -->
                                <div
                                    v-if="
                                        isActiveCheckpoint(
                                            checkpoint.progress
                                        ) && stageMessage
                                    "
                                    class="mt-2 rounded border border-primary/20
                                        bg-primary/5 p-2"
                                >
                                    <p class="text-xs font-medium text-primary">
                                        {{ stageMessage }}
                                    </p>
                                </div>
                            </div>
                        </HoverCardContent>
                    </HoverCard>
                </div>
            </div>
        </div>

        <!-- Progress Percentage -->
        <!-- <div class="text-center">
      <span class="text-2xl font-bold text-gray-800 dark:text-gray-200 tracking-tight">
        {{ Math.round(progress) }}%
      </span>
    </div> -->
    </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { generateRainbowGradient } from '@/utils/animations';
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card';

interface Checkpoint {
    progress: number;
    label: string;
}

interface Props {
    progress: number;
    checkpoints?: Checkpoint[];
    interactive?: boolean;
    currentStage?: string;
    stageMessage?: string;
    mode?: 'lookup' | 'suggestions';
}

// Ensure progress is a number
const normalizedProgress = computed(() => {
    const p = Number(props.progress) || 0;
    return Math.max(0, Math.min(100, p));
});

interface Emits {
    (e: 'progress-change', progress: number): void;
}

const props = withDefaults(defineProps<Props>(), {
    checkpoints: () => [
        { progress: 5, label: 'Start' },
        { progress: 10, label: 'Search Start' },
        { progress: 20, label: 'Search Complete' },
        { progress: 25, label: 'Provider Fetch' },
        { progress: 60, label: 'Providers Complete' },
        { progress: 70, label: 'AI Clustering' },
        { progress: 85, label: 'AI Synthesis' },
        { progress: 95, label: 'Storage' },
        { progress: 100, label: 'Complete' },
    ],
    interactive: false,
});

const emit = defineEmits<Emits>();

// Debug logging
watch(
    () => props.progress,
    (newVal, oldVal) => {
        console.log(`LoadingProgress prop: ${oldVal} → ${newVal}`);
    }
);

watch(normalizedProgress, (newVal, oldVal) => {
    console.log(`LoadingProgress normalized: ${oldVal} → ${newVal}`);
});

watch(
    () => props.currentStage,
    (newVal) => {
        console.log('LoadingProgress stage:', newVal);
    }
);

const progressBarRef = ref<HTMLElement>();
const isDragging = ref(false);

const rainbowGradient = computed(() => generateRainbowGradient(8));

// Get descriptive text for checkpoint stages
const getCheckpointDescription = (progress: number): string => {
    if (props.mode === 'suggestions') {
        const suggestionDescriptions: Record<number, string> = {
            5: 'Initializing AI language models and preparing to analyze your descriptive query.',
            20: 'Validating that your query is seeking word suggestions based on meaning or description.',
            40: 'AI is creatively generating words that match your description, considering nuance and context.',
            80: 'Evaluating and ranking suggestions by relevance, aesthetic quality, and semantic accuracy.',
            100: 'Your curated word suggestions are ready! Each word includes confidence and efflorescence scores.',
        };
        return suggestionDescriptions[progress] || 'Processing your word suggestion request...';
    } else {
        // Default lookup descriptions
        const lookupDescriptions: Record<number, string> = {
            5: 'Pipeline initialization and setup. Preparing search engines and AI processing systems.',
            10: 'Beginning multi-method word search through dictionary indices and semantic databases.',
            20: 'Search complete. Found best matching word across all available sources.',
            25: 'Starting parallel fetches from dictionary providers (Wiktionary, Oxford, Dictionary.com).',
            60: 'All provider data collected. Ready for AI processing and synthesis.',
            70: 'AI analyzing and clustering definitions by semantic meaning to reduce redundancy.',
            85: 'AI synthesizing comprehensive definitions from clustered meanings and generating examples.',
            95: 'Saving processed entry to knowledge base and updating search indices for future lookups.',
            100: 'Pipeline complete! Ready to display comprehensive word information with examples, synonyms, and pronunciation.',
        };
        return lookupDescriptions[progress] || 'Processing pipeline stage...';
    }
};

// Check if a checkpoint is currently active
const isActiveCheckpoint = (checkpointProgress: number): boolean => {
    // Find the current checkpoint range
    const sortedCheckpoints = props.checkpoints.sort(
        (a, b) => a.progress - b.progress
    );
    const currentIndex = sortedCheckpoints.findIndex(
        (cp) => cp.progress >= normalizedProgress.value
    );

    if (currentIndex === -1) {
        // Progress is beyond all checkpoints, check if this is the last one
        return (
            checkpointProgress ===
            sortedCheckpoints[sortedCheckpoints.length - 1].progress
        );
    }

    if (currentIndex === 0) {
        // Progress is at or before first checkpoint
        return checkpointProgress === sortedCheckpoints[0].progress;
    }

    // Progress is between checkpoints, return the previous checkpoint as active
    const activeCheckpoint = sortedCheckpoints[currentIndex];
    return checkpointProgress === activeCheckpoint.progress ;
};

// Handle checkpoint click
const handleCheckpointClick = (checkpoint: Checkpoint) => {
    if (!props.interactive) return;
    emit('progress-change', checkpoint.progress);
};

// Handle progress bar click/drag
const handleProgressBarInteraction = (event: MouseEvent) => {
    if (!props.interactive || !progressBarRef.value) return;

    const rect = progressBarRef.value.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));

    emit('progress-change', percentage);
};

// Mouse drag handlers
const handleMouseDown = (event: MouseEvent) => {
    if (!props.interactive) return;
    isDragging.value = true;
    handleProgressBarInteraction(event);

    const handleMouseMove = (e: MouseEvent) => {
        if (isDragging.value) {
            handleProgressBarInteraction(e);
        }
    };

    const handleMouseUp = () => {
        isDragging.value = false;
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
};
</script>
