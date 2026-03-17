<template>
    <Tooltip>
        <TooltipTrigger as-child>
            <button
                @click="play"
                :disabled="state === 'loading'"
                :aria-label="ariaLabel"
                :class="[
                    'group inline-flex items-center justify-center rounded-full border border-border/50 bg-muted/30 hover:bg-muted hover:border-border transition-all duration-200 opacity-60 hover:opacity-100 disabled:opacity-40 disabled:cursor-wait flex-shrink-0',
                    size === 'lg' ? 'h-10 w-10' : size === 'sm' ? 'h-7 w-7' : 'h-8 w-8',
                    state === 'playing' ? 'animate-pulse' : '',
                ]"
            >
                <Loader2
                    v-if="state === 'loading'"
                    :size="size === 'lg' ? 20 : 14"
                    class="animate-spin text-muted-foreground"
                />
                <VolumeX
                    v-else-if="state === 'error'"
                    :size="size === 'lg' ? 20 : 14"
                    class="text-destructive"
                />
                <Volume2
                    v-else
                    :size="size === 'lg' ? 20 : 14"
                    class="text-muted-foreground group-hover:text-foreground"
                    :class="{ 'text-primary': state === 'playing' }"
                />
            </button>
        </TooltipTrigger>
        <TooltipContent v-if="state === 'error' && errorMessage" side="bottom" :sideOffset="4">
            <p class="text-xs">{{ errorMessage }}</p>
        </TooltipContent>
    </Tooltip>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Volume2, VolumeX, Loader2 } from 'lucide-vue-next';
import { Tooltip, TooltipTrigger, TooltipContent } from '@/components/ui/tooltip';
import type { AudioPlaybackState } from '../composables/useAudioPlayback';

const props = withDefaults(defineProps<{
    state: AudioPlaybackState;
    errorMessage?: string;
    size?: 'sm' | 'md' | 'lg';
}>(), {
    size: 'md',
});

const emit = defineEmits<{
    play: [];
}>();

const play = () => emit('play');

const ariaLabel = computed(() => {
    switch (props.state) {
        case 'loading': return 'Loading pronunciation audio';
        case 'playing': return 'Stop pronunciation audio';
        case 'error': return 'Audio playback failed, click to retry';
        default: return 'Play pronunciation audio';
    }
});
</script>
