<template>
    <Transition
        enter-active-class="transition-all duration-300 ease-out"
        leave-active-class="transition-all duration-200 ease-in"
        enter-from-class="opacity-0 translate-y-2"
        leave-to-class="opacity-0 translate-y-2"
    >
        <div
            v-if="show"
            class="absolute -bottom-2 left-2 right-2 h-1.5 bg-background/80 backdrop-blur-sm rounded-full overflow-hidden shadow-sm"
        >
            <div
                class="h-full rounded-full transition-all duration-300 ease-out"
                :style="{
                    width: `${progress}%`,
                    background: rainbowGradient,
                    boxShadow: '0 0 10px rgba(255, 255, 255, 0.5)',
                }"
            />
        </div>
    </Transition>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface Props {
    show: boolean;
    progress: number;
    segments?: number;
}

const props = withDefaults(defineProps<Props>(), {
    segments: 8,
});

const rainbowGradient = computed(() => {
    const colors = [];
    const hueStep = 360 / props.segments;
    
    for (let i = 0; i < props.segments; i++) {
        const hue = (i * hueStep) % 360;
        colors.push(`hsl(${hue}, 85%, 55%)`);
    }
    
    return `linear-gradient(90deg, ${colors.join(', ')})`;
});
</script>