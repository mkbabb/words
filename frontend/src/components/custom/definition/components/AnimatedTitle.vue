<template>
    <component
        :is="animationComponent"
        v-bind="animationProps"
        class="text-6xl md:text-7xl font-bold leading-tight pb-2"
        style="font-family: 'Fraunces', serif;"
    />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TypewriterText } from '@/components/custom/typewriter';

interface AnimatedTitleProps {
    text: string;
    animationType?: string;
    animationKey: number;
}

const props = withDefaults(defineProps<AnimatedTitleProps>(), {
    animationType: 'typewriter'
});

const animationComponent = computed(() => {
    // Only typewriter is available for now
    return TypewriterText;
});

const animationProps = computed(() => {
    return { 
        text: props.text,
        mode: 'human' as const, // Use human-like typing mode (first animation will be expert)
        baseSpeed: 150, // Faster base speed
        variance: 0.4, // Less variance for more consistent speed
        errorRate: 0.015, // Occasional typos (reduced)
        cursorBlink: true,
        startDelay: 50,
        loop: true // Enable looping to show backspace animations
    };
});
</script>