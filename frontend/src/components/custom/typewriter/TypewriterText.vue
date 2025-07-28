<template>
    <span>
        {{ displayText }}<span v-if="showCursor" :class="cursorClass">|</span>
    </span>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue';
import { useTypewriter } from './composables/useTypewriter';

interface Props {
    text: string;
    mode?: 'basic' | 'human' | 'expert';
    baseSpeed?: number;
    variance?: number;
    errorRate?: number;
    loop?: boolean;
    cursorBlink?: boolean;
    startDelay?: number;
    onComplete?: () => void;
}

const props = withDefaults(defineProps<Props>(), {
    mode: 'human',
    baseSpeed: 250,
    variance: 0.5,
    errorRate: 0.03,
    loop: false,
    cursorBlink: true,
    startDelay: 0
});

const emit = defineEmits<{
    complete: [];
    start: [];
}>();

// Cursor state
const showCursor = ref(true);
const cursorInterval = ref<number | null>(null);

const cursorClass = computed(() => ({
    'inline-block': true,
    'animate-pulse': props.cursorBlink && !typewriter.isTyping.value,
    'text-primary': true,
    'font-light': true
}));

// Initialize typewriter
const typewriter = useTypewriter({
    text: props.text,
    mode: props.mode,
    baseSpeed: props.baseSpeed,
    variance: props.variance,
    errorRate: props.errorRate,
    loop: props.loop,
    onComplete: () => {
        props.onComplete?.();
        emit('complete');
    }
});

const { displayText, isTyping, startTyping, stopTyping, reset, updateText } = typewriter;

// Watch for text changes
watch(() => props.text, (newText, oldText) => {
    stopTyping();
    
    if (newText) {
        // Update the text in the typewriter
        updateText(newText);
        
        // Don't reset if we have text displayed - allow backspace animation
        if (oldText && displayText.value.length > 0) {
            // Text changed but we have existing text - don't reset
            // The startTyping function will handle the backspace animation
            setTimeout(() => {
                emit('start');
                startTyping();
            }, props.startDelay);
        } else {
            // First time or no text displayed - reset and start fresh
            reset();
            setTimeout(() => {
                emit('start');
                startTyping();
            }, props.startDelay);
        }
    }
});

// Start typing on mount
onMounted(() => {
    if (props.text) {
        setTimeout(() => {
            emit('start');
            startTyping();
        }, props.startDelay);
    }

    // Cursor blinking
    if (props.cursorBlink) {
        cursorInterval.value = window.setInterval(() => {
            if (!isTyping.value) {
                showCursor.value = !showCursor.value;
            } else {
                showCursor.value = true;
            }
        }, 530);
    }
});

onUnmounted(() => {
    stopTyping();
    if (cursorInterval.value) {
        clearInterval(cursorInterval.value);
    }
});

// Expose methods for parent components
defineExpose({
    startTyping,
    stopTyping,
    reset,
    isTyping
});
</script>

<style scoped>
@keyframes blink {
    0%, 50% { opacity: 1; }
    51%, 100% { opacity: 0; }
}

.animate-pulse {
    animation: blink 1.06s infinite;
}
</style>