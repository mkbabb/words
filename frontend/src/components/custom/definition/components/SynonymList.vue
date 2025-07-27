<template>
    <div
        v-if="synonyms && synonyms.length > 0"
        class="flex flex-wrap gap-1.5 mt-5"
    >
        <span
            v-for="synonym in synonyms"
            :key="synonym"
            class="text-sm px-2 py-1 rounded-md bg-muted/50 hover:bg-muted text-foreground/80 hover:text-foreground cursor-pointer transition-colors duration-200"
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