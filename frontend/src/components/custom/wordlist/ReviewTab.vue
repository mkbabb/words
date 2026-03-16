<template>
    <div class="space-y-5">
        <!-- Loading -->
        <div v-if="isLoading" class="flex flex-col items-center justify-center py-16 gap-3">
            <div class="h-6 w-6 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <p class="text-sm text-muted-foreground font-serif">Loading review session...</p>
        </div>

        <!-- Empty state -->
        <div v-else-if="dueWords.length === 0" class="py-12">
            <div class="flex flex-col items-center justify-center gap-3 text-center">
                <img :src="yoshiYellowStanding" alt="" class="h-12 w-12" />
                <p class="text-lg font-serif font-semibold text-foreground/80">All caught up</p>
                <p class="text-sm text-muted-foreground font-serif">No words due for review right now. Check back later.</p>
            </div>
        </div>

        <!-- Due words -->
        <div v-else class="space-y-4">
            <!-- Header (left-aligned, plain - matches wordlist title style) -->
            <div>
                <h3 class="text-lg font-serif font-semibold">Due for Review</h3>
                <p class="text-sm text-muted-foreground mt-0.5 font-serif">
                    {{ dueWords.length }} {{ dueWords.length === 1 ? 'word' : 'words' }} ready
                    <template v-if="leechCount > 0">
                        <span class="mx-1">&middot;</span>
                        <span class="text-destructive/80">{{ leechCount }} {{ leechCount === 1 ? 'leech' : 'leeches' }}</span>
                    </template>
                </p>
            </div>

            <!-- Word cards grid -->
            <div class="grid gap-x-2 gap-y-1.5 grid-cols-[repeat(auto-fill,minmax(140px,1fr))]">
                <BaseWordCard
                    v-for="word in dueWords"
                    :key="word.word"
                    :word="word.word"
                    :variant="word.mastery_level"
                    @click="toggleWord(word.word)"
                >
                    <template #overlay>
                        <div
                            :class="[
                                'flex h-4 w-4 shrink-0 items-center justify-center rounded-[4px] border transition-all duration-200',
                                selectedWords.has(word.word)
                                    ? 'border-primary bg-primary shadow-sm'
                                    : 'border-border/60 bg-background/50'
                            ]"
                        >
                            <Check v-if="selectedWords.has(word.word)" class="h-3 w-3 text-primary-foreground" />
                        </div>
                    </template>

                    <template #meta>
                        <!-- State badge + metadata -->
                        <div class="flex flex-wrap items-center gap-1.5">
                            <span
                                :class="[
                                    'inline-flex items-center rounded-full px-1.5 py-px text-[10px] font-medium',
                                    getCardStateBadgeClasses(word.card_state),
                                ]"
                            >
                                {{ getCardStateLabelFull(word.card_state) }}
                            </span>
                            <span
                                v-if="word.is_leech"
                                class="inline-flex items-center rounded-full bg-destructive/10 border border-destructive/20 px-1.5 py-px text-[10px] font-medium text-destructive"
                            >
                                Leech
                            </span>
                        </div>

                        <!-- Ease / Interval -->
                        <div class="mt-0.5 flex items-center gap-1 text-[11px] text-muted-foreground tabular-nums">
                            <span>{{ word.ease_factor.toFixed(1) }}</span>
                            <span class="opacity-30">&middot;</span>
                            <span>{{ formatInterval(word.interval_days) }}</span>
                            <template v-if="word.lapse_count > 0">
                                <span class="opacity-30">&middot;</span>
                                <span class="text-destructive/60">{{ word.lapse_count }}L</span>
                            </template>
                        </div>
                    </template>
                </BaseWordCard>
            </div>

            <!-- Floating action dock -->
            <Teleport to="body">
                <Transition
                    enter-active-class="transition-all duration-300 ease-apple-spring"
                    enter-from-class="translate-y-4 opacity-0"
                    enter-to-class="translate-y-0 opacity-100"
                    leave-active-class="transition-all duration-200 ease-apple-smooth"
                    leave-from-class="translate-y-0 opacity-100"
                    leave-to-class="translate-y-4 opacity-0"
                >
                    <div
                        v-if="dueWords.length > 0"
                        class="fixed bottom-6 left-1/2 -translate-x-1/2 z-bar"
                    >
                        <GlassDock :start-collapsed="false" manual>
                            <TooltipProvider :delay-duration="300">
                                <div class="flex items-center gap-1.5">
                                    <Tooltip v-if="selectedWords.size > 0 && selectedWords.size < dueWords.length">
                                        <TooltipTrigger as-child>
                                            <button
                                                class="flex h-10 w-10 items-center justify-center rounded-full bg-background/40 backdrop-blur-sm transition-colors hover:bg-background/70 text-muted-foreground hover:text-foreground"
                                                @click="clearSelection"
                                            >
                                                <X :size="16" />
                                            </button>
                                        </TooltipTrigger>
                                        <TooltipContent>Clear selection</TooltipContent>
                                    </Tooltip>
                                    <Tooltip>
                                        <TooltipTrigger as-child>
                                            <button
                                                class="flex h-10 w-10 items-center justify-center rounded-full bg-background/40 backdrop-blur-sm transition-colors hover:bg-background/70 text-muted-foreground hover:text-foreground"
                                                @click="toggleSelectAll"
                                            >
                                                <ListX v-if="selectedWords.size === dueWords.length" :size="16" />
                                                <ListChecks v-else :size="16" />
                                            </button>
                                        </TooltipTrigger>
                                        <TooltipContent>{{ selectedWords.size === dueWords.length ? 'Deselect all' : 'Select all' }}</TooltipContent>
                                    </Tooltip>
                                    <Tooltip>
                                        <TooltipTrigger as-child>
                                            <button
                                                class="flex h-10 w-10 items-center justify-center rounded-full bg-background/40 backdrop-blur-sm transition-colors hover:bg-background/70 text-muted-foreground hover:text-foreground"
                                                @click="shuffleWords"
                                            >
                                                <Shuffle :size="16" />
                                            </button>
                                        </TooltipTrigger>
                                        <TooltipContent>Shuffle order</TooltipContent>
                                    </Tooltip>
                                    <div class="h-6 w-px bg-border/50 shrink-0" />
                                    <Button
                                        size="sm"
                                        class="h-10 rounded-full px-5"
                                        @click="handleStartReview"
                                    >
                                        Start Review ({{ selectedWords.size > 0 ? selectedWords.size : dueWords.length }})
                                    </Button>
                                </div>
                            </TooltipProvider>
                        </GlassDock>
                    </div>
                </Transition>
            </Teleport>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { Check, X, ListChecks, ListX, Shuffle } from 'lucide-vue-next';
import yoshiYellowStanding from '@/assets/yoshi/standing/yoshi_yellow_standing.png';
import { Button } from '@/components/ui/button';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '@/components/ui/tooltip';
import { GlassDock } from '@/components/custom/animation';
import { wordlistApi } from '@/api';
import type { DueWordItem } from '@/types/wordlist';
import BaseWordCard from './BaseWordCard.vue';
import {
    formatInterval,
    getCardStateBadgeClasses,
    getCardStateLabelFull,
} from './utils/formatting';

interface Props {
    wordlistId: string;
}

interface Emits {
    (e: 'start-review', selectedWords?: string[]): void;
}

const props = defineProps<Props>();
const emit = defineEmits<Emits>();

const isLoading = ref(false);
const dueWords = ref<DueWordItem[]>([]);
const selectedWords = ref<Set<string>>(new Set());

const leechCount = computed(() =>
    dueWords.value.filter((w) => w.is_leech).length
);

async function fetchDueWords() {
    if (!props.wordlistId) return;
    isLoading.value = true;
    try {
        const response = await wordlistApi.getReviewSession(props.wordlistId, 50);
        const data = response.data ?? response;
        dueWords.value = data.words ?? [];
        // Default: all selected
        selectedWords.value = new Set(dueWords.value.map((w) => w.word));
    } catch {
        dueWords.value = [];
    } finally {
        isLoading.value = false;
    }
}

function toggleWord(word: string) {
    const next = new Set(selectedWords.value);
    if (next.has(word)) {
        next.delete(word);
    } else {
        next.add(word);
    }
    selectedWords.value = next;
}

function toggleSelectAll() {
    if (selectedWords.value.size === dueWords.value.length) {
        selectedWords.value = new Set();
    } else {
        selectedWords.value = new Set(dueWords.value.map((w) => w.word));
    }
}

function clearSelection() {
    selectedWords.value = new Set();
}

function shuffleWords() {
    const arr = [...dueWords.value];
    for (let i = arr.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [arr[i], arr[j]] = [arr[j], arr[i]];
    }
    dueWords.value = arr;
}

function handleStartReview() {
    const words = selectedWords.value.size > 0 ? Array.from(selectedWords.value) : undefined;
    emit('start-review', words);
}

// Refetch when wordlist changes
watch(
    () => props.wordlistId,
    () => fetchDueWords(),
    { immediate: true }
);

// Expose refresh method for parent
defineExpose({ refresh: fetchDueWords });
</script>
