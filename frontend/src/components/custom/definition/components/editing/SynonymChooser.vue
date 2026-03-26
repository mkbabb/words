<template>
    <CardContent
        v-if="synonymChooser?.essay"
        class="mt-6 mb-4 space-y-3 border-t border-border/50 px-4 pt-6 sm:px-6"
    >
        <h3 class="mb-3 text-xl font-semibold tracking-wide">
            Choose the Right Synonym
        </h3>
        <div
            class="rounded-lg border border-border/30 bg-card px-4 py-3 shadow-sm transition-fast hover:border-border/50 hover:bg-card/90"
        >
            <p class="text-sm font-serif leading-relaxed text-foreground whitespace-pre-line">
                {{ synonymChooser.essay }}
            </p>

            <!-- Synonym comparison chips -->
            <div
                v-if="synonymChooser.synonyms_compared?.length"
                class="mt-3 flex flex-wrap gap-2 border-t border-border/20 pt-3"
            >
                <div
                    v-for="(syn, i) in synonymChooser.synonyms_compared"
                    :key="i"
                    class="group cursor-pointer rounded-lg border border-border/30 bg-background px-3 py-1.5 text-sm transition-[color,background-color,border-color] hover:border-primary/30 hover:bg-primary/5"
                    @click="$emit('searchWord', syn.word)"
                >
                    <span class="font-medium text-primary">{{ syn.word }}</span>
                    <span class="ml-1 text-xs text-muted-foreground">
                        — {{ syn.distinction }}
                    </span>
                </div>
            </div>
        </div>
    </CardContent>
</template>

<script setup lang="ts">
import { CardContent } from '@/components/ui/card';
import type { SynonymChooser } from '@/types/api';

defineProps<{
    synonymChooser: SynonymChooser | null | undefined;
}>();

defineEmits<{
    searchWord: [word: string];
}>();
</script>
