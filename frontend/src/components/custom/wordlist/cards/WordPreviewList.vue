<template>
    <div v-if="parsedWords.length > 0" class="space-y-4">
        <ThemedCard
            variant="default"
            class-name="space-y-4 p-4 sm:p-5"
            :texture-enabled="true"
            texture-type="clean"
            texture-intensity="subtle"
            hide-star
        >
            <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="space-y-1">
                    <p class="text-xs uppercase tracking-[0.22em] text-muted-foreground">
                        Words found
                    </p>
                    <h3 class="font-serif text-lg font-semibold">
                        Parsed output
                    </h3>
                    <p class="text-sm text-muted-foreground">
                        {{ formatCount(parsedWords.length) }} unique words
                        <span class="text-muted-foreground/50">·</span>
                        {{ formatCount(totalFrequency) }} total occurrences
                    </p>
                </div>

                <div class="flex flex-wrap items-center justify-end gap-2">
                    <Button @click="showAll = !showAll" variant="ghost" size="sm">
                        {{ showAll ? 'Show Less' : 'Show All' }}
                    </Button>
                    <Button
                        @click="$emit('review-all')"
                        variant="outline"
                        size="sm"
                        :disabled="reviewCandidates.length === 0"
                    >
                        Review
                    </Button>
                    <Button
                        @click="$emit('reconcile-all')"
                        size="sm"
                        :disabled="reviewCandidates.length === 0"
                    >
                        Reconcile all
                    </Button>
                    <Button
                        @click="$emit('ignore-all')"
                        variant="ghost"
                        size="sm"
                        :disabled="reviewCandidates.length === 0"
                    >
                        Ignore all
                    </Button>
                </div>
            </div>

            <div
                class="grid gap-4 lg:grid-cols-[minmax(0,1.45fr)_minmax(0,1fr)]"
            >
                <div class="card-surface space-y-2 p-3">
                    <div class="flex items-center justify-between">
                        <h4 class="text-sm font-medium">Parsed words</h4>
                        <span class="text-xs text-muted-foreground">
                            Showing {{ formatCount(displayedWords.length) }}
                        </span>
                    </div>

                    <div class="max-h-72 overflow-y-auto pr-1">
                        <div class="space-y-1.5">
                            <div
                                v-for="word in displayedWords"
                                :key="`${word.text}-${word.frequency}`"
                                class="flex items-start justify-between gap-3 rounded-xl border border-border/30 bg-background/50 px-3 py-2 shadow-sm"
                            >
                                <div class="min-w-0">
                                    <p class="truncate font-serif text-sm font-semibold">
                                        {{ word.resolvedText || word.text }}
                                    </p>
                                    <p
                                        v-if="word.resolvedText && word.resolvedText !== word.text"
                                        class="text-micro text-muted-foreground"
                                    >
                                        from "{{ word.text }}"
                                    </p>
                                </div>
                                <div class="flex shrink-0 items-center gap-2 text-xs text-muted-foreground">
                                    <span v-if="word.frequency > 1" class="tabular-nums">
                                        {{ formatCount(word.frequency) }}x
                                    </span>
                                    <span
                                        v-if="word.notes"
                                        class="rounded-full bg-muted/70 px-2 py-0.5 text-micro"
                                    >
                                        {{ word.notes }}
                                    </span>
                                </div>
                            </div>
                        </div>

                        <div
                            v-if="!showAll && parsedWords.length > 10"
                            class="pt-3 text-center"
                        >
                            <span class="text-xs text-muted-foreground">
                                ... and {{ parsedWords.length - 10 }} more
                            </span>
                        </div>
                    </div>
                </div>

                <div class="space-y-3">
                    <div class="card-surface space-y-3 p-3">
                        <div class="flex items-center justify-between gap-3">
                            <div>
                                <h4 class="text-sm font-medium">
                                    Reconcile review
                                </h4>
                                <p class="text-xs text-muted-foreground">
                                    Review likely misspellings or close variants before upload.
                                </p>
                            </div>
                            <span
                                class="rounded-full bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary tabular-nums"
                            >
                                {{ formatCount(pendingCount) }} pending
                            </span>
                        </div>

                        <div
                            v-if="isLoadingReconcile"
                            class="flex items-center gap-2 rounded-xl border border-dashed border-border/40 bg-background/40 p-3 text-sm text-muted-foreground"
                        >
                            <svg class="h-4 w-4 animate-spin text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            Checking words against the dictionary...
                        </div>

                        <div
                            v-else-if="reviewCandidates.length === 0"
                            class="rounded-xl border border-dashed border-border/40 bg-background/40 p-3 text-sm text-muted-foreground"
                        >
                            All words look good — no likely misspellings or close variants detected.
                        </div>

                        <div v-else class="space-y-2">
                            <div
                                v-for="candidate in reviewCandidates"
                                :key="candidate.id"
                                :class="[
                                    'rounded-xl border p-3 transition-colors',
                                    candidate.status === 'accepted'
                                        ? 'border-emerald-500/30 bg-emerald-500/10'
                                        : candidate.status === 'ignored'
                                          ? 'border-border/30 bg-muted/40 opacity-70'
                                          : 'border-border/30 bg-background/60',
                                ]"
                            >
                                <div class="flex items-start justify-between gap-3">
                                    <div class="min-w-0">
                                        <p class="truncate font-serif text-sm font-semibold">
                                            {{ candidate.sourceText }}
                                        </p>
                                        <p class="text-xs text-muted-foreground">
                                            Did you mean <span class="font-medium text-foreground">{{ candidate.suggestedText }}</span>?
                                        </p>
                                        <p class="mt-1 text-micro text-muted-foreground">
                                            {{ candidate.reason }} · {{ Math.round(candidate.score * 100) }}% match
                                        </p>
                                    </div>

                                    <div class="flex shrink-0 items-center gap-1">
                                        <Button
                                            size="sm"
                                            variant="outline"
                                            :disabled="candidate.status === 'accepted'"
                                            @click="$emit('accept-candidate', candidate.id)"
                                        >
                                            Use suggestion
                                        </Button>
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            class="text-muted-foreground"
                                            :disabled="candidate.status === 'ignored'"
                                            @click="$emit('ignore-candidate', candidate.id)"
                                        >
                                            Ignore
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </ThemedCard>
    </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { Button } from '@/components/ui/button';
import { ThemedCard } from '@/components/custom/card';
import { formatCount } from '../utils/formatting';
import type { ParsedWord } from '../composables/useWordlistFileParser';
import type { ReviewCandidate } from '../composables/useWordlistReconcilePreview';

const props = defineProps<{
    parsedWords: ParsedWord[];
    reviewCandidates: Array<ReviewCandidate & { status: 'pending' | 'accepted' | 'ignored' }>;
    isLoadingReconcile?: boolean;
}>();

defineEmits<{
    'review-all': [];
    'reconcile-all': [];
    'ignore-all': [];
    'accept-candidate': [candidateId: string];
    'ignore-candidate': [candidateId: string];
}>();

const showAll = ref(false);

const displayedWords = computed(() =>
    showAll.value ? props.parsedWords : props.parsedWords.slice(0, 10)
);

const totalFrequency = computed(() =>
    props.parsedWords.reduce((sum, word) => sum + (word.frequency || 1), 0)
);

const pendingCount = computed(() =>
    props.reviewCandidates.filter((candidate) => candidate.status === 'pending').length
);
</script>
