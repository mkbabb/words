<template>
    <div
        v-if="suggestion && suggestion !== query"
        :class="[
            'search-input-overlay pointer-events-none absolute inset-0 overflow-hidden whitespace-nowrap text-lg',
            'text-muted-foreground/50',
        ]"
        :style="{
            textAlign: textAlign,
            lineHeight: 'var(--search-line-height, 1.4)',
            minHeight: 'var(--search-min-h, 48px)',
        }"
    >
        <span class="invisible whitespace-pre">{{ query }}</span
        ><span class="truncate">{{ suggestion.slice(query.length) }}</span>
    </div>
</template>

<script setup lang="ts">
interface AutocompleteOverlayProps {
    query: string;
    suggestion: string;
    textAlign?: 'left' | 'center' | 'right';
}

withDefaults(defineProps<AutocompleteOverlayProps>(), {
    textAlign: 'left',
});
</script>

<style scoped>
.search-input-overlay {
    box-sizing: border-box;
    display: flex;
    align-items: flex-start;
    padding-inline: var(--search-pad-start, 1rem) var(--search-pad-end, 1rem);
    padding-block: var(--search-text-pad-y, calc((var(--search-min-h, 48px) - 1.1em) / 2));
}
</style>
