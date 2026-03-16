<template>
    <ThemedCard
        :variant="variant"
        :class="[
            'group relative cursor-pointer px-2 pt-2 pb-1 transition-all duration-300 ease-apple-default hover:z-10 hover:scale-[1.02] hover:shadow-card-hover sm:px-2.5 sm:pt-2.5 sm:pb-1.5',
            className,
        ]"
        texture-enabled
        texture-type="clean"
        texture-intensity="subtle"
        hide-star
        @click="$emit('click')"
    >
        <!-- Word name -->
        <div class="pr-6">
            <button
                v-if="linkable"
                class="truncate font-serif font-semibold text-sm leading-tight text-left
                       decoration-primary/30 underline-offset-4 decoration-1
                       hover:underline cursor-pointer outline-none
                       transition-colors group-hover:text-primary sm:text-base"
                @click.stop="$emit('lookup')"
            >
                {{ word.toLowerCase() }}
            </button>
            <span v-else class="font-serif font-semibold text-sm leading-tight sm:text-base">
                {{ word.toLowerCase() }}
            </span>
        </div>

        <!-- Metadata slot -->
        <div v-if="$slots.meta" class="mt-1">
            <slot name="meta" />
        </div>

        <!-- Overlay slot (top-right corner, e.g. checkbox or action menu) -->
        <div v-if="$slots.overlay" class="absolute top-1.5 right-1.5 z-10">
            <slot name="overlay" />
        </div>

        <!-- Default slot for additional content -->
        <slot />
    </ThemedCard>
</template>

<script setup lang="ts">
import { ThemedCard } from '@/components/custom/card';
import type { MasteryLevel } from '@/types/wordlist';

withDefaults(defineProps<{
    word: string;
    variant?: MasteryLevel;
    className?: string;
    linkable?: boolean;
}>(), {
    linkable: false,
});

defineEmits<{
    click: [];
    lookup: [];
}>();
</script>
