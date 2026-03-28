<template>
    <Transition
        enter-active-class="transition-normal"
        leave-active-class="transition-[opacity,transform] duration-200 ease-in"
        enter-from-class="opacity-0 translate-y-2"
        leave-to-class="opacity-0 translate-y-2"
    >
        <div
            v-if="show"
            class="pointer-events-none absolute -bottom-2 left-0 right-0 z-overlay overflow-x-clip"
        >
            <div
                class="pointer-events-auto cursor-pointer"
                @click.stop="handleClick"
                title="Click to show detailed progress"
            >
                <LoadingProgress
                    :progress="progress"
                    variant="thin"
                    :interactive="true"
                    :current-stage="currentStage"
                    :stage-message="stageMessage"
                    :mode="mode"
                    :category="category"
                    @progress-change="handleProgressChange"
                />
            </div>
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { LoadingProgress } from '@/components/custom/loading';

interface Props {
    show: boolean;
    progress: number;
    currentStage?: string;
    stageMessage?: string;
    mode?: 'lookup' | 'suggestions' | 'upload' | 'image' | string;
    category?: string;
}

interface Emits {
    (e: 'click'): void;
    (e: 'progress-change', progress: number): void;
}

withDefaults(defineProps<Props>(), {
    mode: 'lookup',
});

const emit = defineEmits<Emits>();

const handleClick = (event: Event) => {
    event.stopPropagation();
    emit('click');
};

const handleProgressChange = (progress: number) => {
    // When progress changes (from checkpoint clicks), also show the modal
    emit('progress-change', progress);
    emit('click'); // This will show the modal
};
</script>
