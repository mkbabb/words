<template>
    <div class="ml-auto flex items-center gap-2">
        <span class="text-micro text-muted-foreground/50">Freq</span>
        <div class="relative flex items-center">
            <div
                class="h-1.5 w-16 rounded-full"
                :style="{ background: TEMPERATURE_GRADIENT }"
            />
            <input
                type="range"
                min="0"
                max="100"
                :value="(value || 3) * 20"
                class="freq-slider absolute inset-0 h-1.5 w-16 cursor-pointer appearance-none bg-transparent"
                :style="{
                    '--thumb-color': temperatureColor((value || 3) / 5),
                }"
                @input="handleInput"
            />
        </div>
        <span
            class="min-w-[1ch] text-center text-micro font-mono font-medium"
            :style="{
                color: temperatureColor((value || 3) / 5),
            }"
        >
            {{ value || '—' }}
        </span>
    </div>
</template>

<script setup lang="ts">
import { TEMPERATURE_GRADIENT, temperatureColor } from '@/utils/animations';

interface Props {
    value: number;
}

defineProps<Props>();

const emit = defineEmits<{
    'update:value': [value: number];
}>();

function handleInput(e: Event) {
    const raw = Math.round(
        parseInt((e.target as HTMLInputElement).value) / 20,
    );
    const clamped = Math.max(1, Math.min(5, raw));
    emit('update:value', clamped);
}
</script>

<style scoped>
.freq-slider::-webkit-slider-thumb {
    appearance: none;
    height: 12px;
    width: 12px;
    border-radius: 9999px;
    background: var(--thumb-color, hsl(40, 80%, 55%));
    border: 2px solid hsl(var(--background));
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
    transition: transform 0.15s ease;
}
.freq-slider::-webkit-slider-thumb:hover {
    transform: scale(1.25);
}
.freq-slider::-moz-range-thumb {
    height: 12px;
    width: 12px;
    border-radius: 9999px;
    background: var(--thumb-color, hsl(40, 80%, 55%));
    border: 2px solid hsl(var(--background));
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.15);
}
</style>
