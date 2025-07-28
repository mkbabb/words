<template>
    <div class="word-suggestions-container">
        <div v-if="wordSuggestions" class="space-y-4">

            <!-- Suggestion Cards Grid -->
            <div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <HoverCard
                    v-for="(suggestion, index) in sortedSuggestions"
                    :key="suggestion.word"
                    :open-delay="200"
                    :close-delay="100"
                >
                    <HoverCardTrigger as-child>
                        <ThemedCard
                            :variant="getCardVariant(index)"
                            class="group relative cursor-pointer transition-all duration-500 ease-apple-spring hover:scale-[1.03]"
                            @click="handleWordClick(suggestion.word)"
                        >
                            <div class="p-3">
                        <!-- Word with confidence indicator -->
                        <div class="mb-3 flex items-center justify-between">
                            <h3 class="text-xl font-bold transition-colors group-hover:text-primary">
                                {{ suggestion.word }}
                            </h3>
                            <div class="flex items-center gap-2">
                                <!-- Confidence meter -->
                                <div class="relative h-2 w-16 overflow-hidden rounded-full bg-muted">
                                    <div 
                                        class="absolute inset-y-0 left-0 bg-gradient-to-r from-amber-400 to-yellow-500 transition-all duration-500"
                                        :style="{ width: `${suggestion.confidence * 100}%` }"
                                    />
                                </div>
                                <!-- Efflorescence sparkle -->
                                <div 
                                    v-if="suggestion.efflorescence > 0.7"
                                    class="text-yellow-500 animate-pulse"
                                >
                                    ✨
                                </div>
                            </div>
                        </div>

                        <!-- Example usage if available -->
                        <div v-if="suggestion.example_usage" class="mb-3">
                            <p 
                                class="text-sm text-muted-foreground italic"
                                v-html="formatExampleUsage(suggestion.example_usage)"
                            />
                        </div>


                        <!-- Metrics -->
                        <div class="mt-3 flex gap-4 text-xs text-muted-foreground">
                            <span>Relevance: {{ formatPercent(suggestion.confidence) }}</span>
                            <span>Efflorescence: {{ formatPercent(suggestion.efflorescence) }}</span>
                        </div>
                    </div>

                            <!-- Click indicator -->
                            <div class="absolute inset-x-0 bottom-0 h-1 bg-gradient-to-r from-transparent via-primary/50 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
                        </ThemedCard>
                    </HoverCardTrigger>
                    <HoverCardContent class="w-80" side="top" align="center">
                        <div class="space-y-2">
                            <p class="text-sm font-medium">{{ suggestion.word }}</p>
                            <p class="text-sm text-muted-foreground">
                                {{ suggestion.reasoning }}
                            </p>
                        </div>
                    </HoverCardContent>
                </HoverCard>
            </div>

            <!-- Original Query Reference -->
            <div class="mt-8 flex justify-center">
                <div class="rounded-lg border border-border bg-muted/30 px-4 py-3">
                    <p class="fira-code text-sm italic text-muted-foreground">
                        "{{ originalQuery }}"
                    </p>
                </div>
            </div>
        </div>

        <!-- Empty State -->
        <div v-else class="flex min-h-[400px] items-center justify-center">
            <div class="text-center">
                <p class="text-lg text-muted-foreground">No word suggestions available</p>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useAppStore } from '@/stores';
import { ThemedCard } from '@/components/custom/card';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';

const store = useAppStore();

const wordSuggestions = computed(() => store.wordSuggestions);

const sortedSuggestions = computed(() => {
    if (!wordSuggestions.value) return [];
    // Sort by confidence first, then by efflorescence
    return [...wordSuggestions.value.suggestions].sort((a, b) => {
        const confidenceDiff = b.confidence - a.confidence;
        if (Math.abs(confidenceDiff) > 0.1) return confidenceDiff;
        return b.efflorescence - a.efflorescence;
    });
});

const originalQuery = computed(() => wordSuggestions.value?.original_query || '');

function getCardVariant(index: number): 'default' | 'gold' | 'silver' | 'bronze' {
    if (index === 0) return 'gold';
    if (index === 1) return 'silver';
    if (index === 2) return 'bronze';
    return 'default';
}

function formatPercent(value: number): string {
    return `${Math.round(value * 100)}%`;
}

function formatExampleUsage(example: string): string {
    // Bold the suggested word in the example
    return example.replace(/\*\*(.*?)\*\*/g, '<strong class="font-bold text-foreground">$1</strong>');
}

async function handleWordClick(word: string) {
    // After successful lookup, smoothly transition to dictionary mode
    store.mode = 'dictionary';
    // Use searchWord for direct lookup (sets isDirectLookup flag)
    await store.searchWord(word);
}
</script>

<style scoped>
.reasoning-container {
    transition: max-height 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
</style>