<template>
    <div
        v-if="showButton"
        :class="[
            'flex flex-shrink-0 items-center justify-center overflow-hidden transition-all ease-out',
            `duration-${animationDuration}`
        ]"
        :style="{
            opacity: opacity,
            transform: `scale(${minScale + opacity * (maxScale - minScale)})`,
            pointerEvents: opacity > opacityThreshold ? 'auto' : 'none',
            width: opacity > opacityThreshold ? `${expandedWidth}px` : '0px',
            marginLeft: opacity > opacityThreshold ? `${spacing}px` : '0px',
        }"
    >
        <button
            @click="$emit('regenerate')"
            @mouseenter="handleHover"
            @mouseleave="handleLeave"
            :class="[
                'flex h-12 w-12 items-center justify-center rounded-lg',
                'transition-all duration-200 ease-out',
                aiMode
                    ? 'hover:bg-amber-100/60 dark:hover:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                    : 'hover:bg-muted/50',
                forceRefreshMode && aiMode
                    ? 'bg-amber-200/60 text-amber-800 dark:bg-amber-800/40 dark:text-amber-200'
                    : forceRefreshMode
                    ? 'bg-primary/20 text-primary'
                    : ''
            ]"
            :title="
                forceRefreshMode
                    ? 'Force refresh mode ON - Next lookup will regenerate'
                    : 'Toggle force refresh mode'
            "
        >
            <RefreshCw
                :size="20"
                :style="{
                    transform: `rotate(${rotation}deg)`,
                    transition: 'transform 700ms cubic-bezier(0.175, 0.885, 0.32, 1.4)',
                }"
            />
        </button>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { RefreshCw } from 'lucide-vue-next';

interface RegenerateButtonProps {
    showButton: boolean;
    opacity: number;
    aiMode?: boolean;
    // Animation parameters
    minScale?: number;
    maxScale?: number;
    opacityThreshold?: number;
    expandedWidth?: number;
    spacing?: number;
    animationDuration?: number;
}

const props = withDefaults(defineProps<RegenerateButtonProps>(), {
    aiMode: false,
    minScale: 0.9,
    maxScale: 1.0,
    opacityThreshold: 0.1,
    expandedWidth: 48,
    spacing: 8,
    animationDuration: 300
});

// Using defineModel for two-way binding of forceRefreshMode
const forceRefreshMode = defineModel<boolean>('forceRefreshMode', { required: true });

const emit = defineEmits<{
    'regenerate': [];
}>();

const rotation = ref(0);

const handleHover = () => {
    rotation.value += 180;
};

const handleLeave = () => {
    rotation.value -= 180;
};

// Props and emit are used in template
void props;
void emit;

// Expose rotation for parent to animate on click
defineExpose({
    rotate: (degrees: number) => {
        rotation.value += degrees;
    }
});
</script>