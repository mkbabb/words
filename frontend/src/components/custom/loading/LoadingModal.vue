<template>
    <Modal v-model="modelValue" :close-on-backdrop="allowDismiss">
        <div class="flex flex-col items-center space-y-6">
            <AnimatedText
                :text="displayText || word || ''"
                text-class="text-[clamp(1.5rem,8vw,3.75rem)] font-black pb-8"
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
                :category="category"
                @progress-change="$emit('progress-change', $event)"
            />

            <!-- Stage Description Text -->
            <div class="max-w-md text-center space-y-2">
                <ShimmerText
                    :text="currentStageText"
                    text-class="text-[clamp(1rem,4vw,1.25rem)] font-semibold italic text-gray-800 dark:text-gray-100"
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
import { getDefaultStages, getStageMessage, getStageDescription } from './pipeline-stages';


interface Props {
    modelValue: boolean;
    word?: string;
    displayText?: string;
    progress: number;
    currentStage: string;
    allowDismiss?: boolean;
    mode?: 'lookup' | 'suggestions';
    dynamicCheckpoints?: Array<{progress: number, label: string, description: string}>;
    category?: string;
}

interface Emits {
    (e: 'update:modelValue', value: boolean): void;
    (e: 'progress-change', progress: number): void;
}

const props = withDefaults(defineProps<Props>(), {
    allowDismiss: false,
    mode: 'lookup',
    dynamicCheckpoints: undefined,
    category: undefined,
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

    // Use category first, then mode as fallback
    const category = props.category || props.mode || 'lookup';
    return getStageMessage(category, props.currentStage);
});

const progressTextClass = computed(() => ({
    'animate-pulse': props.progress < 100,
    'text-green-600 dark:text-green-400': props.progress >= 100,
}));

// Computed property for stage description using centralized config
const stageDescription = computed(() => {
    // Use category first, then mode as fallback
    const category = props.category || props.mode || 'lookup';
    return getStageDescription(category, props.currentStage);
});

// Pass through the model value
const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

// Use dynamic checkpoints if provided, otherwise fall back to centralized defaults
const progressCheckpoints = computed(() => {
    // If dynamic checkpoints are provided, use them
    if (props.dynamicCheckpoints && props.dynamicCheckpoints.length > 0) {
        return props.dynamicCheckpoints;
    }
    
    // Otherwise use centralized defaults
    const category = props.category || props.mode || 'lookup';
    const stages = getDefaultStages(category);
    return stages.map(stage => ({
        progress: stage.progress,
        label: stage.label
    }));
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
