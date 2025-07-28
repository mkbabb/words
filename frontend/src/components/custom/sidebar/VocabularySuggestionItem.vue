<template>
    <div
        @click="$emit('click', suggestion)"
        class="group border-border from-primary/5 to-primary/10 hover:from-primary/10 hover:to-primary/15 cursor-pointer rounded-lg border bg-gradient-to-br p-3 transition-all duration-200 hover:shadow-sm"
    >
        <div class="flex items-start justify-between">
            <div class="min-w-0 flex-1">
                <p class="truncate text-sm font-medium">
                    {{ suggestion.word }}
                </p>
                <p class="text-muted-foreground mt-1 line-clamp-2 text-xs">
                    {{ suggestion.reasoning || suggestion.reason }}
                </p>
            </div>
            <div class="ml-2 flex-shrink-0">
                <span
                    class="text-primary bg-primary/20 inline-flex h-5 w-5 items-center justify-center rounded-full text-xs font-medium"
                >
                    {{ suggestion.difficulty_level || '?' }}
                </span>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
interface VocabularySuggestion {
    word: string;
    reasoning?: string;
    reason?: string;
    difficulty_level?: number;
}

defineProps<{
    suggestion: VocabularySuggestion;
}>();

defineEmits<{
    click: [suggestion: VocabularySuggestion];
}>();
</script>