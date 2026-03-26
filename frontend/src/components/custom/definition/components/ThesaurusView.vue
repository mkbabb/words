<template>
    <!-- Empty/Error State for Thesaurus -->
    <CardContent
        v-if="
            !thesaurusData ||
            !thesaurusData.synonyms ||
            thesaurusData.synonyms.length === 0
        "
        class="space-y-6 px-3 sm:px-6"
    >
        <ErrorState
            :title="getEmptyThesaurusTitle()"
            :message="getEmptyThesaurusMessage()"
            error-type="empty"
            :retryable="true"
            @retry="$emit('retry-thesaurus')"
        />
        <div class="flex justify-center">
            <Button
                variant="outline"
                size="sm"
                @click="$emit('switch-to-dictionary')"
            >
                Switch to Dictionary
            </Button>
        </div>
    </CardContent>

    <!-- Thesaurus Content -->
    <CardContent
        v-else-if="thesaurusData && thesaurusData.synonyms.length > 0"
        class="space-y-6 px-3 sm:px-6"
    >
        <div
            v-if="activeSource && activeSource !== 'synthesis'"
            class="text-xs text-muted-foreground/70"
        >
            Synonyms from {{ formatProviderName(activeSource) }}
        </div>
        <div :style="{ height: `${totalSize}px`, position: 'relative', width: '100%' }">
            <div
                v-for="virtualRow in virtualItems"
                :key="String(virtualRow.key)"
                :style="{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%',
                    minHeight: '48px',
                    transform: `translateY(${virtualRow.start}px)`,
                }"
            >
                <div class="grid grid-cols-3 gap-1.5 sm:grid-cols-3 sm:gap-2 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
                    <HoverCard
                        v-for="synonym in getRowData(virtualRow.index) ?? []"
                        :key="synonym.word"
                        :open-delay="400"
                        :close-delay="100"
                    >
                        <HoverCardTrigger as-child>
                            <Card
                                :class="
                                    cn(
                                        'h-full cursor-pointer overflow-hidden hover-lift-md hover:shadow-md',
                                        getHeatmapClass(synonym.score)
                                    )
                                "
                                @click="$emit('word-click', synonym.word)"
                            >
                                <CardContent class="px-2 py-0.5 sm:py-1">
                                    <div
                                        class="truncate text-base font-medium sm:text-sm"
                                    >
                                        {{ synonym.word }}
                                    </div>
                                    <div class="text-sm opacity-75 sm:text-xs">
                                        {{ Math.round(synonym.score * 100) }}%
                                    </div>
                                </CardContent>
                            </Card>
                        </HoverCardTrigger>
                        <HoverCardContent
                            :class="
                                cn(
                                    'themed-hovercard z-hovercard w-80',
                                    cardVariant !== 'default' ? 'shadow-cartoon-sm' : ''
                                )
                            "
                            :data-theme="cardVariant || 'default'"
                            side="top"
                            align="center"
                        >
                            <div class="space-y-3">
                                <div>
                                    <h4 class="mb-3 text-base font-semibold">
                                        {{ synonym.word }}
                                    </h4>
                                </div>

                                <div class="space-y-2 text-sm">
                                    <div
                                        class="flex items-center justify-between border-b border-border/30 py-1"
                                    >
                                        <span class="text-muted-foreground"
                                            >Similarity Score</span
                                        >
                                        <span class="font-medium"
                                            >{{
                                                Math.round(synonym.score * 100)
                                            }}%</span
                                        >
                                    </div>

                                    <div
                                        v-if="synonym.confidence"
                                        class="flex items-center justify-between border-b border-border/30 py-1"
                                    >
                                        <span class="text-muted-foreground"
                                            >Confidence</span
                                        >
                                        <span class="font-medium"
                                            >{{
                                                Math.round(synonym.confidence * 100)
                                            }}%</span
                                        >
                                    </div>

                                    <div
                                        v-if="synonym.efflorescence_score"
                                        class="flex items-center justify-between border-b border-border/30 py-1"
                                    >
                                        <span class="text-muted-foreground"
                                            >Efflorescence</span
                                        >
                                        <div class="flex items-center gap-1">
                                            <span class="font-medium">{{
                                                synonym.efflorescence_score.toFixed(1)
                                            }}</span>
                                            <Sparkles class="h-3 w-3 text-amber-500" />
                                        </div>
                                    </div>

                                    <div
                                        v-if="synonym.language_origin"
                                        class="flex items-center justify-between border-b border-border/30 py-1"
                                    >
                                        <span class="text-muted-foreground"
                                            >Origin</span
                                        >
                                        <span class="font-medium">{{
                                            synonym.language_origin
                                        }}</span>
                                    </div>

                                    <div
                                        v-if="synonym.part_of_speech"
                                        class="flex items-center justify-between py-1"
                                    >
                                        <span class="text-muted-foreground"
                                            >Part of Speech</span
                                        >
                                        <span class="font-medium">{{
                                            synonym.part_of_speech
                                        }}</span>
                                    </div>
                                </div>

                                <div
                                    v-if="synonym.usage_note"
                                    class="border-t border-border/30 pt-2"
                                >
                                    <p class="text-xs text-muted-foreground italic">
                                        {{ synonym.usage_note }}
                                    </p>
                                </div>
                            </div>
                        </HoverCardContent>
                    </HoverCard>
                </div>
            </div>
        </div>
    </CardContent>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useElementSize, useParentElement } from '@vueuse/core';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    HoverCard,
    HoverCardContent,
    HoverCardTrigger,
} from '@/components/ui/hover-card';
import { Sparkles } from 'lucide-vue-next';
import { cn } from '@/utils';
import { getHeatmapClass } from '../utils/formatting';
import { ErrorState } from './';
import { useVirtualGrid } from '@/composables/virtual';
import type { ThesaurusEntry, CardVariant, SynonymData } from '@/types';

interface ThesaurusViewProps {
    thesaurusData: ThesaurusEntry | null;
    cardVariant: CardVariant;
    activeSource?: string;
}

const props = defineProps<ThesaurusViewProps>();

// Virtual grid setup
const SYNONYM_MIN_WIDTH = 120;
const SYNONYM_GAP = 8;
const parentEl = useParentElement();
const { width: containerWidth } = useElementSize(parentEl);
const columnCount = computed(() => {
    const w = containerWidth.value;
    if (w <= 0) return 3;
    return Math.max(3, Math.min(6, Math.floor((w + SYNONYM_GAP) / (SYNONYM_MIN_WIDTH + SYNONYM_GAP))));
});

const synonyms = computed(() => props.thesaurusData?.synonyms ?? []);

const { totalSize, virtualItems, getRowData } = useVirtualGrid<SynonymData>({
    items: synonyms,
    totalCount: () => synonyms.value.length,
    columnCount,
    rowHeight: 48,
});

const formatProviderName = (provider: string) => {
    const names: Record<string, string> = {
        wiktionary: 'Wiktionary',
        oxford: 'Oxford',
        apple_dictionary: 'Apple Dictionary',
        merriam_webster: 'Merriam-Webster',
        free_dictionary: 'Free Dictionary',
        wordhippo: 'WordHippo',
    };
    return names[provider] || provider.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

defineEmits<{
    'word-click': [word: string];
    'retry-thesaurus': [];
    'switch-to-dictionary': [];
}>();

// Helper functions for error states
const getEmptyThesaurusTitle = () => {
    return 'No Synonyms Found';
};

const getEmptyThesaurusMessage = () => {
    return "No synonyms were found for this word. This might be a specialized term or proper noun that doesn't have common alternatives.";
};
</script>
