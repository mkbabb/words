<template>
    <div
        :class="[
            'flex-shrink-0 overflow-hidden transition-all ease-out',
            `duration-${animationDuration}`
        ]"
        :style="{
            opacity: opacity,
            transform: `scale(${minScale + opacity * (maxScale - minScale)})`,
            pointerEvents: opacity > opacityThreshold ? 'auto' : 'none',
            width: opacity > opacityThreshold ? `${expandedWidth}px` : '0px',
            marginLeft: showRegenerateButton && opacity > opacityThreshold ? `${spacing}px` : '0px',
        }"
    >
        <HamburgerIcon
            :is-open="modelValue"
            :ai-mode="aiMode"
            @toggle="modelValue = !modelValue"
        />
    </div>
</template>

<script setup lang="ts">
import { HamburgerIcon } from '@/components/custom/icons';

interface HamburgerButtonProps {
    opacity: number;
    showRegenerateButton?: boolean;
    aiMode?: boolean;
    // Animation parameters
    minScale?: number;
    maxScale?: number;
    opacityThreshold?: number;
    expandedWidth?: number;
    spacing?: number;
    animationDuration?: number;
}

const props = withDefaults(defineProps<HamburgerButtonProps>(), {
    showRegenerateButton: false,
    aiMode: false,
    minScale: 0.9,
    maxScale: 1.0,
    opacityThreshold: 0.1,
    expandedWidth: 48,
    spacing: 8,
    animationDuration: 300
});

// Using defineModel for two-way binding (modern Vue 3.4+)
const modelValue = defineModel<boolean>({ required: true });

// Props are used in template
void props;
</script>