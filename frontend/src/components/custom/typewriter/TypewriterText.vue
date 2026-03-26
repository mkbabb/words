<template>
    <span class="tw-root">
        <span
            v-for="(char, index) in leadingChars"
            :key="index"
            class="cursor-pointer hover:bg-muted/50 transition-colors duration-150 rounded-sm px-0.5 -mx-0.5"
            @click="handleCharClick(index)"
        >
            {{ char }}
        </span>
        <span v-if="tailChar !== null" class="tw-tail">
            <span
                class="cursor-pointer hover:bg-muted/50 transition-colors duration-150 rounded-sm px-0.5 -mx-0.5"
                @click="handleCharClick(displayTextChars.length - 1)"
            >
                {{ tailChar }}
            </span>
            <span
                v-if="cursorVisible"
                class="tw-cursor text-primary font-light"
                :class="{
                    'tw-cursor--blink': cursorBlink && !typewriter.isTyping.value,
                }"
            >
                {{ cursorChar }}
            </span>
        </span>
        <span
            v-else-if="cursorVisible"
            class="tw-cursor text-primary font-light"
            :class="{
                'tw-cursor--blink': cursorBlink && !typewriter.isTyping.value,
            }"
        >
            {{ cursorChar }}
        </span>
    </span>
</template>

<script setup lang="ts">
import { watch, onMounted, onUnmounted, computed } from 'vue';
import { useTypewriter } from './composables/useTypewriter';

interface Props {
    text: string;
    ngramSize?: number | { min: number; max: number };
    baseSpeed?: number;
    variance?: number;
    errorRate?: number;
    firstAnimationSpeedFactor?: number;
    maxCharsBeforeNotice?: number;
    continueAfterTypoProbability?: number;
    sequentialTypoDecay?: number;
    correctionSpeedMultiplier?: number;
    cursorVisible?: boolean;
    cursorBlink?: boolean;
    cursorChar?: string;
    startDelay?: number;
    loop?: boolean;
    respectReducedMotion?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    ngramSize: () => ({ min: 1, max: 3 }),
    baseSpeed: 150,
    variance: 0.4,
    errorRate: 0.015,
    firstAnimationSpeedFactor: 0.6,
    maxCharsBeforeNotice: 4,
    continueAfterTypoProbability: 0.6,
    sequentialTypoDecay: 0.3,
    correctionSpeedMultiplier: 0.5,
    cursorVisible: true,
    cursorBlink: true,
    cursorChar: '|',
    startDelay: 0,
    loop: false,
    respectReducedMotion: true,
});

const emit = defineEmits<{
    complete: [];
    start: [];
}>();

const typewriter = useTypewriter({
    text: props.text,
    ngramSize: props.ngramSize,
    baseSpeed: props.baseSpeed,
    variance: props.variance,
    errorRate: props.errorRate,
    firstAnimationSpeedFactor: props.firstAnimationSpeedFactor,
    maxCharsBeforeNotice: props.maxCharsBeforeNotice,
    continueAfterTypoProbability: props.continueAfterTypoProbability,
    sequentialTypoDecay: props.sequentialTypoDecay,
    correctionSpeedMultiplier: props.correctionSpeedMultiplier,
    cursorVisible: props.cursorVisible,
    cursorBlink: props.cursorBlink,
    cursorChar: props.cursorChar,
    loop: props.loop,
    respectReducedMotion: props.respectReducedMotion,
    onComplete: () => emit('complete'),
});

const { displayText, startTyping, stopTyping, reset, backspaceToPosition } = typewriter;

const displayTextChars = computed(() => displayText.value.split(''));
const leadingChars = computed(() => displayTextChars.value.slice(0, -1));
const tailChar = computed(() =>
    displayTextChars.value.length > 0
        ? displayTextChars.value[displayTextChars.value.length - 1]
        : null,
);

function handleCharClick(clickedIndex: number) {
    if (clickedIndex >= displayText.value.length) return;

    if (typewriter.isTyping.value) {
        stopTyping();
        setTimeout(() => backspaceToPosition(clickedIndex + 1), 50);
    } else {
        backspaceToPosition(clickedIndex + 1);
    }
}

watch(
    () => props.text,
    (newText, oldText) => {
        if (newText !== oldText && newText) {
            stopTyping();
            typewriter.updateText(newText);
            setTimeout(() => {
                emit('start');
                startTyping();
            }, props.startDelay);
        }
    },
);

onMounted(() => {
    if (props.text) {
        setTimeout(() => {
            emit('start');
            startTyping();
        }, props.startDelay);
    }
});

onUnmounted(() => {
    stopTyping();
});

defineExpose({
    startTyping,
    stopTyping,
    reset,
    isTyping: typewriter.isTyping,
});
</script>

<style scoped>
.tw-root {
    display: inline;
}

.tw-tail {
    white-space: nowrap;
}

.tw-cursor {
    display: inline-block;
}

.tw-cursor--blink {
    animation: tw-cursor-blink 1.06s step-end infinite;
}

@keyframes tw-cursor-blink {
    0%,
    50% {
        opacity: 1;
    }
    51%,
    100% {
        opacity: 0;
    }
}
</style>
