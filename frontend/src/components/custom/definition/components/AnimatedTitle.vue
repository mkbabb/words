<template>
    <component
        :is="animationComponent"
        v-bind="animationProps"
        :key="`${animationType}-${animationKey}`"
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
    const customStyles = {
        color: 'var(--color-foreground)',
        position: 'relative' as const,
        textShadow: '0 1px 2px rgba(0,0,0,0.1)',
        backgroundImage: 'var(--paper-aged-texture)',
        backgroundSize: '100px 100px',
        backgroundRepeat: 'repeat',
        backgroundClip: 'text',
        WebkitBackgroundClip: 'text',
        backgroundAttachment: 'scroll',
        backgroundPosition: '0 0',
    };
    
    return { 
        text: props.text,
        mode: 'human', // Use human-like typing mode (first animation will be expert)
        baseSpeed: 150, // Faster base speed
        variance: 0.4, // Less variance for more consistent speed
        errorRate: 0.015, // Occasional typos (reduced)
        cursorBlink: true,
        startDelay: 50,
        loop: false // No looping for title animations
    };
});
</script>