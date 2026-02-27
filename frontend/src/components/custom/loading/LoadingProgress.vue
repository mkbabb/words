<template>
    <div :class="[
        'flex w-full flex-col gap-1',
        variant === 'thin' ? '' : 'space-y-4'
    ]">
        <!-- Progress Bar -->
        <div class="relative">
            <div
                ref="progressBarRef"
                class="relative overflow-hidden rounded-full bg-gray-200
                    dark:bg-gray-700"
                :class="[
                    variant === 'thin' ? 'h-1.5' : 'h-8',
                    variant === 'thin' ? 'bg-background/80 backdrop-blur-sm shadow-sm' : 'shadow-inner border border-gray-300 dark:border-gray-600',
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
                        boxShadow: variant === 'thin' ? '0 0 10px rgba(255, 255, 255, 0.5)' : undefined,
                    }"
                    :class="[
                        variant === 'thin' ? '' : 'shadow-lg',
                        normalizedProgress < 100 ? 'animate-pulse' : '',
                    ]"
                    :data-progress="normalizedProgress"
                />
            </div>

            <!-- Checkpoint Markers -->
            <div class="absolute top-0 bottom-0 w-full">
                <div
                    v-for="(checkpoint, index) in effectiveCheckpoints"
                    :key="index"
                    class="absolute flex items-center justify-center"
                    :style="{
                        left: checkpoint.progress === 0 
                            ? '0%' 
                            : checkpoint.progress === 100 
                                ? '100%' 
                                : `${checkpoint.progress}%`,
                        top: '50%',
                        transform: checkpoint.progress === 0 
                            ? 'translateY(-50%)' 
                            : checkpoint.progress === 100 
                                ? 'translateX(-100%) translateY(-50%)' 
                                : 'translateX(-50%) translateY(-50%)',
                    }"
                >
                    <HoverCard :open-delay="100" :close-delay="50">
                        <HoverCardTrigger as-child>
                            <button
                                class="rounded-full transition-all duration-300 outline-none"
                                :class="[
                                    variant === 'thin' ? 'h-2 w-2 border' : 'h-6 w-6 border-2',
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
                                @click.stop="handleCheckpointClick(checkpoint)"
                                :aria-label="`${checkpoint.label} - ${checkpoint.progress}%`"
                            />
                        </HoverCardTrigger>
                        <HoverCardContent
                            class="z-[10000] w-60"
                            side="top"
                            :side-offset="variant === 'thin' ? 8 : 16"
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
                                        getCheckpointDescriptionText(
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
import { computed, ref, onMounted, onUnmounted } from 'vue';
import { generateRainbowGradient } from '@/utils/animations';
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card';
import { getDefaultStages, getCheckpointDescription } from './pipeline-stages';
import { logger } from '@/utils/logger';

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
    mode?: 'lookup' | 'suggestions' | 'upload' | 'image' | string;
    category?: string; // Process category for dynamic descriptions
    variant?: 'default' | 'thin'; // Add variant prop
}

// Ensure progress is a number
const normalizedProgress = computed(() => {
    const p = Number(props.progress) || 0;
    return Math.max(0, Math.min(100, p));
});

interface Emits {
    (e: 'progress-change', progress: number): void;
}

// Convert pipeline stages to checkpoint format
const convertToCheckpoints = (stages: Array<{progress: number, label: string, description: string}>): Checkpoint[] => {
    return stages.map(stage => ({
        progress: stage.progress,
        label: stage.label
    }));
};

const props = withDefaults(defineProps<Props>(), {
    checkpoints: undefined, // Will be computed dynamically
    interactive: false,
    mode: 'lookup',
    variant: 'default',
});

// Compute checkpoints dynamically if not provided
const effectiveCheckpoints = computed(() => {
    if (props.checkpoints) {
        return props.checkpoints;
    }
    
    // Use category first, then mode as fallback
    const category = props.category || props.mode || 'lookup';
    const stages = getDefaultStages(category);
    return convertToCheckpoints(stages);
});

const emit = defineEmits<Emits>();

const progressBarRef = ref<HTMLElement>();
const isDragging = ref(false);
const isMounted = ref(false);

const rainbowGradient = computed(() => generateRainbowGradient(8));

// Get descriptive text for checkpoint stages using centralized config
const getCheckpointDescriptionText = (progress: number): string => {
    const category = props.category || props.mode || 'lookup';
    return getCheckpointDescription(category, progress);
};

// Check if a checkpoint is currently active
const isActiveCheckpoint = (checkpointProgress: number): boolean => {
    // Find the current checkpoint range
    const sortedCheckpoints = effectiveCheckpoints.value.sort(
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
    if (!props.interactive || !progressBarRef.value || !isMounted.value) return;

    // Add comprehensive null checks for getBoundingClientRect to prevent runtime errors
    try {
        // Additional check: ensure element is still connected to DOM
        if (!progressBarRef.value.isConnected) {
            logger.warn('LoadingProgress: Element no longer connected to DOM');
            return;
        }

        const rect = progressBarRef.value.getBoundingClientRect();
        if (!rect || rect.width === 0) return;
        
        const x = event.clientX - rect.left;
        const percentage = Math.max(0, Math.min(100, (x / rect.width) * 100));

        emit('progress-change', percentage);
    } catch (error) {
        logger.warn('LoadingProgress: Failed to get bounding rect during interaction:', error);
    }
};

// Mouse drag handlers
const handleMouseDown = (event: MouseEvent) => {
    if (!props.interactive || !isMounted.value) return;
    isDragging.value = true;
    handleProgressBarInteraction(event);

    const handleMouseMove = (e: MouseEvent) => {
        if (isDragging.value && isMounted.value) {
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

// Lifecycle management
onMounted(() => {
    isMounted.value = true;
});

onUnmounted(() => {
    isMounted.value = false;
    
    // Clean up any ongoing drag operations
    if (isDragging.value) {
        isDragging.value = false;
        // Remove any lingering event listeners
        document.removeEventListener('mousemove', () => {});
        document.removeEventListener('mouseup', () => {});
    }
    
    // Clear any refs that might be accessed by Reka UI
    progressBarRef.value = undefined;
});
</script>
