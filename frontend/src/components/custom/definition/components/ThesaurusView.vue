<template>
    <!-- Empty/Error State for Thesaurus -->
    <CardContent
        v-if="!thesaurusData || !thesaurusData.synonyms || thesaurusData.synonyms.length === 0"
        class="space-y-6 px-3 sm:px-6"
    >
        <ErrorState
            :title="getEmptyThesaurusTitle()"
            :message="getEmptyThesaurusMessage()"
            error-type="no-synonyms"
            :retryable="true"
            @retry="$emit('retry-thesaurus')"
        />
    </CardContent>

    <!-- Thesaurus Content -->
    <CardContent
        v-else-if="thesaurusData && thesaurusData.synonyms.length > 0"
        class="space-y-6 px-3 sm:px-6"
    >
        <div
            class="grid grid-cols-3 gap-1.5 sm:gap-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
        >
            <HoverCard 
                v-for="synonym in thesaurusData.synonyms"
                :key="synonym.word"
                :open-delay="400"
                :close-delay="100"
            >
                <HoverCardTrigger as-child>
                    <Card
                        :class="cn(
                            'cursor-pointer transition-all duration-300 hover:scale-105 hover:shadow-md overflow-hidden h-full',
                            getHeatmapClass(synonym.score)
                        )"
                        @click="$emit('word-click', synonym.word)"
                    >
                        <CardContent class="px-2 py-0.5 sm:py-1">
                            <div class="font-medium text-base sm:text-sm truncate">
                                {{ synonym.word }}
                            </div>
                            <div class="text-sm sm:text-xs opacity-75">
                                {{ Math.round(synonym.score * 100) }}%
                            </div>
                        </CardContent>
                    </Card>
                </HoverCardTrigger>
                <HoverCardContent 
                    :class="cn(
                        'themed-hovercard w-80 z-[80]',
                        cardVariant !== 'default' ? 'themed-shadow-sm' : ''
                    )"
                    :data-theme="cardVariant || 'default'"
                    side="top"
                    align="center"
                >
                    <div class="space-y-3">
                        <div>
                            <h4 class="text-base font-semibold mb-3">{{ synonym.word }}</h4>
                        </div>
                        
                        <div class="space-y-2 text-sm">
                            <div class="flex justify-between items-center py-1 border-b border-border/30">
                                <span class="text-muted-foreground">Similarity Score</span>
                                <span class="font-medium">{{ Math.round(synonym.score * 100) }}%</span>
                            </div>
                            
                            <div v-if="synonym.confidence" class="flex justify-between items-center py-1 border-b border-border/30">
                                <span class="text-muted-foreground">Confidence</span>
                                <span class="font-medium">{{ Math.round(synonym.confidence * 100) }}%</span>
                            </div>
                            
                            <div v-if="synonym.efflorescence_score" class="flex justify-between items-center py-1 border-b border-border/30">
                                <span class="text-muted-foreground">Efflorescence</span>
                                <div class="flex items-center gap-1">
                                    <span class="font-medium">{{ synonym.efflorescence_score.toFixed(1) }}</span>
                                    <Sparkles class="h-3 w-3 text-amber-500" />
                                </div>
                            </div>
                            
                            <div v-if="synonym.language_origin" class="flex justify-between items-center py-1 border-b border-border/30">
                                <span class="text-muted-foreground">Origin</span>
                                <span class="font-medium">{{ synonym.language_origin }}</span>
                            </div>
                            
                            <div v-if="synonym.part_of_speech" class="flex justify-between items-center py-1">
                                <span class="text-muted-foreground">Part of Speech</span>
                                <span class="font-medium">{{ synonym.part_of_speech }}</span>
                            </div>
                        </div>
                        
                        <div v-if="synonym.usage_note" class="pt-2 border-t border-border/30">
                            <p class="text-xs text-muted-foreground italic">{{ synonym.usage_note }}</p>
                        </div>
                    </div>
                </HoverCardContent>
            </HoverCard>
        </div>
    </CardContent>
</template>

<script setup lang="ts">
import { Card, CardContent } from '@/components/ui/card';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '@/components/ui/hover-card';
import { Sparkles } from 'lucide-vue-next';
import { cn } from '@/utils';
import { getHeatmapClass } from '../utils/formatting';
import { ErrorState } from './';
import type { ThesaurusEntry, CardVariant } from '@/types';

interface ThesaurusViewProps {
    thesaurusData: ThesaurusEntry | null;
    cardVariant: CardVariant;
}

defineProps<ThesaurusViewProps>();

defineEmits<{
    'word-click': [word: string];
    'retry-thesaurus': [];
}>();

// Helper functions for error states
const getEmptyThesaurusTitle = () => {
    return 'No Synonyms Found';
};

const getEmptyThesaurusMessage = () => {
    return 'No synonyms were found for this word. This might be a specialized term or proper noun that doesn\'t have common alternatives.';
};
</script>