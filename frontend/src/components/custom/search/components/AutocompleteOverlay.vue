<template>
    <div
        v-if="suggestion && suggestion !== query"
        :class="[
            'pointer-events-none absolute inset-0 overflow-hidden whitespace-nowrap text-lg',
            'text-muted-foreground/50',
        ]"
        :style="{
            paddingLeft: paddingLeft,
            paddingRight: paddingRight,
            paddingTop: '0.75rem',
            paddingBottom: '0.75rem',
            textAlign: textAlign,
            lineHeight: '1.4',
            minHeight: '48px',
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
    paddingLeft?: string;
    paddingRight?: string;
    textAlign?: 'left' | 'center' | 'right';
}

withDefaults(defineProps<AutocompleteOverlayProps>(), {
    paddingLeft: '1rem',
    paddingRight: '1rem',
    textAlign: 'left',
});
</script>
