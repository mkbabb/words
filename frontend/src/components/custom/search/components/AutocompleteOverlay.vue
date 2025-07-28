<template>
    <div
        v-if="suggestion && suggestion !== query"
        :class="[
            'pointer-events-none absolute top-0 left-0 right-0 flex h-12 items-center text-lg transition-all duration-300 ease-out',
            'text-muted-foreground/50 truncate'
        ]"
        :style="{
            paddingLeft: paddingLeft,
            paddingRight: paddingRight,
            textAlign: textAlign
        }"
    >
        <span class="invisible whitespace-pre">{{ query }}</span><span class="truncate">{{ suggestion.slice(query.length) }}</span>
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
    textAlign: 'left'
});
</script>