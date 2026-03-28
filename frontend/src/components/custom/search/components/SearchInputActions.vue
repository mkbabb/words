<template>
    <div
        :class="[
            'absolute z-controls flex items-center gap-1',
            aiMode ? 'right-2 bottom-2' : 'top-1/2 right-2 -translate-y-1/2',
        ]"
    >
        <!-- Expand Button -->
        <Transition
            enter-active-class="transition-fast"
            leave-active-class="transition-[opacity,transform] duration-200 ease-in"
            enter-from-class="opacity-0 scale-90"
            leave-to-class="opacity-0 scale-90"
        >
            <Button
                v-if="aiMode && scrollProgress < 0.3"
                variant="ai"
                size="icon"
                :class="[
                    'h-[var(--search-slot-size,2rem)] w-[var(--search-slot-size,2rem)] rounded-xl p-0',
                ]"
                :style="{
                    opacity: 1 - scrollProgress * 3,
                    transform: `scale(${1 - scrollProgress * 0.5})`,
                }"
                @click.stop="$emit('expand')"
                title="Expand for longer input"
            >
                <Maximize2 class="h-4 w-4" />
            </Button>
        </Transition>

        <!-- Clear Button -->
        <Transition
            enter-active-class="transition-fast"
            leave-active-class="transition-[opacity,transform] duration-200 ease-in"
            enter-from-class="opacity-0 scale-90"
            leave-to-class="opacity-0 scale-90"
        >
            <Button
                v-if="showClear"
                :variant="aiMode ? 'ai' : 'glass-subtle'"
                size="icon"
                @click.stop="$emit('clear')"
                :class="[
                    'h-[var(--search-slot-size,2rem)] w-[var(--search-slot-size,2rem)] rounded-xl p-0',
                ]"
                title="Clear search"
            >
                <X class="h-4 w-4" />
            </Button>
        </Transition>
    </div>
</template>

<script setup lang="ts">
import { Maximize2, X } from 'lucide-vue-next';
import { Button } from '@mkbabb/glass-ui';

defineProps<{
    aiMode: boolean;
    showClear: boolean;
    scrollProgress: number;
}>();

defineEmits<{
    expand: [];
    clear: [];
}>();
</script>
