<template>
    <component
        :is="animationComponent"
        v-bind="animationProps"
        class="pb-2 text-[clamp(1.5rem,10vw,4.5rem)] leading-tight font-bold font-serif"
    />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { TypewriterText } from '@/components/custom/typewriter';

interface AnimatedTitleProps {
    text: string;
}

const props = defineProps<AnimatedTitleProps>();

const animationComponent = TypewriterText;

const animationProps = computed(() => ({
    text: props.text,
    ngramSize: { min: 1, max: 2 },
    baseSpeed: 120,
    variance: 0.35,
    errorRate: 0.015,
    firstAnimationSpeedFactor: 0.6,
    maxCharsBeforeNotice: 3,
    correctionSpeedMultiplier: 0.4,
    cursorVisible: true,
    cursorBlink: true,
    startDelay: 50,
    loop: false,
}));
</script>
