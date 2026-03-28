<template>
    <button
        :ref="(el) => $emit('set-ref', el as HTMLButtonElement, index)"
        :class="[
            'interactive-item ease-apple-spring flex w-full items-center justify-between border-l-4 border-transparent px-4 py-3 text-left transition-[background-color,color,box-shadow,transform] duration-250 transform-gpu',
            'active:scale-[0.97]',
            selected
                ? 'border-l-primary/60 bg-accent/35 shadow-sm'
                : 'hover:bg-accent/15 hover:shadow-sm',
        ]"
        @click="$emit('select', { word: result.word, score: result.score || 1.0, method: result.method || SearchMethod.EXACT })"
        @mouseenter="$emit('hover', index)"
    >
        <span
            :class="[
                'transition-[color,font-weight,transform] duration-200 ease-apple-smooth',
                selected &&
                    'font-semibold text-primary',
            ]"
        >
            {{ (result.word ?? '').toLowerCase() }}
        </span>
        <div class="flex items-center gap-2 text-xs">
            <!-- Mastery badge (wordlist context) -->
            <span
                v-if="result.mastery_level"
                :class="[
                    'inline-block rounded-full px-2 py-0.5',
                    result.mastery_level === 'gold' &&
                        'bg-amber-300/10 text-amber-600 dark:text-amber-400',
                    result.mastery_level === 'silver' &&
                        'bg-gray-300/10 text-gray-600 dark:text-gray-400',
                    result.mastery_level === 'bronze' &&
                        'bg-orange-300/10 text-orange-600 dark:text-orange-400',
                    result.mastery_level === 'default' &&
                        'bg-muted text-muted-foreground',
                    selected && 'font-semibold',
                ]"
            >
                {{ result.mastery_level }}
            </span>
            <!-- Frequency -->
            <span
                v-if="result.frequency != null"
                :class="[
                    'text-muted-foreground',
                    selected && 'font-semibold text-primary',
                ]"
            >
                {{ formatCount(result.frequency) }}x
            </span>
            <!-- Wordlist name (aggregate results) -->
            <span
                v-if="result.wordlist_name"
                class="max-w-[80px] truncate rounded-full bg-muted/60 px-1.5 py-0.5 text-[10px] text-muted-foreground"
            >
                {{ result.wordlist_name }}
            </span>
            <!-- Primary method pill -->
            <span
                v-if="result.method"
                :class="[
                    'inline-block rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                    methodPillClass(result.method),
                ]"
            >
                {{ methodAbbrev(result.method) }}
            </span>
            <!-- Score -->
            <span
                :class="[
                    'font-medium text-muted-foreground',
                    selected && 'font-semibold text-primary',
                ]"
            >
                {{ result.score != null ? Math.round(result.score * 100) + '%' : '' }}
            </span>
            <!-- Info popover for multi-match -->
            <Popover v-if="result.matches && result.matches.length > 1">
                <PopoverTrigger as-child>
                    <button
                        class="flex h-5 w-5 items-center justify-center rounded-full text-muted-foreground/60 transition-[background-color,color,transform] duration-200 ease-apple-smooth hover:bg-accent/35 hover:text-foreground hover:scale-105"
                        @click.stop
                    >
                        <Info class="h-3 w-3" />
                    </button>
                </PopoverTrigger>
                <PopoverContent class="w-52 rounded-xl border border-border/40 bg-background/96 p-3 shadow-cartoon-lg backdrop-blur-xl" side="left" :side-offset="8">
                    <p class="mb-2 text-xs font-semibold text-muted-foreground">Match Details</p>
                    <div class="space-y-1.5">
                        <div
                            v-for="m in result.matches"
                            :key="m.method"
                            class="flex items-center gap-2 text-xs"
                        >
                            <span
                                :class="[
                                    'inline-block w-16 rounded-full px-1.5 py-0.5 text-center text-[10px] font-medium',
                                    methodPillClass(m.method),
                                ]"
                            >
                                {{ m.method }}
                            </span>
                            <div class="flex-1 h-1.5 rounded-full bg-muted/60 overflow-hidden">
                                <div
                                    class="h-full rounded-full transition-[width,background-color] duration-300 ease-apple-smooth"
                                    :class="methodBarClass(m.method)"
                                    :style="{ width: Math.round(m.score * 100) + '%' }"
                                />
                            </div>
                            <span class="tabular-nums text-muted-foreground w-8 text-right">
                                {{ Math.round(m.score * 100) }}%
                            </span>
                        </div>
                    </div>
                </PopoverContent>
            </Popover>
        </div>
    </button>
</template>

<script setup lang="ts">
import { Info } from 'lucide-vue-next';
import { SearchMethod } from '@/types/api';
import { Popover, PopoverContent, PopoverTrigger } from '@mkbabb/glass-ui';
import { formatCount } from '@/components/custom/wordlist/utils/formatting';

interface UnifiedResult {
    word: string;
    score: number;
    method?: string;
    matches?: Array<{ method: string; score: number }>;
    mastery_level?: string;
    frequency?: number;
    wordlist_id?: string;
    wordlist_name?: string;
}

interface Props {
    result: UnifiedResult;
    index: number;
    selected: boolean;
}

defineProps<Props>();

defineEmits<{
    select: [result: any];
    hover: [index: number];
    'set-ref': [el: HTMLButtonElement | null, index: number];
}>();

// Method pill styling
function methodPillClass(method: string): string {
    switch (method) {
        case 'exact': return 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400';
        case 'prefix': return 'bg-blue-500/10 text-blue-600 dark:text-blue-400';
        case 'substring': return 'bg-cyan-500/10 text-cyan-600 dark:text-cyan-400';
        case 'fuzzy': return 'bg-amber-500/10 text-amber-600 dark:text-amber-400';
        case 'semantic': return 'bg-purple-500/10 text-purple-600 dark:text-purple-400';
        default: return 'bg-muted text-muted-foreground';
    }
}

function methodBarClass(method: string): string {
    switch (method) {
        case 'exact': return 'bg-emerald-500';
        case 'prefix': return 'bg-blue-500';
        case 'substring': return 'bg-cyan-500';
        case 'fuzzy': return 'bg-amber-500';
        case 'semantic': return 'bg-purple-500';
        default: return 'bg-muted-foreground';
    }
}

function methodAbbrev(method: string): string {
    switch (method) {
        case 'exact': return 'ex';
        case 'prefix': return 'pfx';
        case 'substring': return 'sub';
        case 'fuzzy': return 'fz';
        case 'semantic': return 'sem';
        default: return method;
    }
}
</script>
