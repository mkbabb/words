<template>
    <div
        v-if="synonyms && synonyms.length > 0"
        class="mt-5 flex flex-wrap gap-1.5"
    >
        <span
            v-for="synonym in synonyms"
            :key="synonym"
            class="cursor-pointer rounded-md border border-border/50 bg-muted/50 px-2 py-1 text-sm text-foreground/80 transition-all duration-200 hover:border-border hover:bg-muted hover:text-foreground"
            @click="$emit('synonym-click', synonym)"
        >
            {{ synonym }}
        </span>
    </div>
</template>

<script setup lang="ts">
interface SynonymListProps {
    synonyms: string[];
}

defineProps<SynonymListProps>();

defineEmits<{
    'synonym-click': [word: string];
}>();
</script>
