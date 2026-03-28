<template>
    <!-- Vertical layout mode -->
    <div v-if="layout === 'vertical' && (showSynthesis || providers.length > 0)" class="flex flex-col items-center gap-2">
        <!-- AI Synthesis icon -->
        <Tooltip v-if="showSynthesis">
            <TooltipTrigger as-child>
                <button
                    :disabled="!interactive"
                    @click="$emit('select-source', 'synthesis')"
                    :class="[
                        'flex h-10 w-10 items-center justify-center rounded-full border shadow-sm transform-gpu transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-250 ease-apple-spring',
                        activeSource === 'synthesis'
                            ? 'border-amber-500/40 bg-amber-500/12 text-amber-600 dark:border-amber-400/40 dark:text-amber-400 ring-2 ring-amber-500/20'
                            : interactive
                              ? 'border-border/40 bg-background/96 text-muted-foreground/80 opacity-70 hover:border-border/60 hover:bg-background hover:opacity-100 hover:-translate-y-0.5 hover:scale-105'
                              : 'cursor-default border-border/50 bg-background text-muted-foreground/50 opacity-60',
                    ]"
                >
                    <Wand2 :size="20" />
                </button>
            </TooltipTrigger>
            <TooltipContent side="left" :side-offset="6">
                AI Synthesis
            </TooltipContent>
        </Tooltip>

        <!-- Provider icons — each on its own line -->
        <Tooltip v-for="provider in orderedProviders" :key="provider">
            <TooltipTrigger as-child>
                <button
                    :disabled="!interactive"
                    @click="$emit('select-source', provider)"
                    :class="[
                        'flex h-10 w-10 items-center justify-center rounded-full border bg-background/96 shadow-sm transform-gpu transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-250 ease-apple-spring',
                        interactive ? 'cursor-pointer hover:-translate-y-0.5 hover:scale-105 hover:bg-background hover:shadow-md' : 'cursor-default',
                        activeSource === provider
                            ? 'border-primary/40 ring-2 ring-primary/20 bg-primary/10'
                            : 'border-border/30',
                    ]"
                >
                    <component
                        :is="getProviderIcon(provider)"
                        :size="20"
                        class="text-muted-foreground"
                    />
                </button>
            </TooltipTrigger>
            <TooltipContent side="left" :side-offset="6">
                {{ getProviderDisplayName(provider) }}
            </TooltipContent>
        </Tooltip>

        <!-- Info button for metadata popover -->
        <Popover v-if="providers.length > 1" v-model:open="popoverOpen">
            <PopoverTrigger as-child>
                <button
                    class="flex h-6 w-6 items-center justify-center rounded-full text-muted-foreground/40 transition-[background-color,color,transform] duration-200 ease-apple-smooth hover:bg-background/90 hover:text-muted-foreground hover:scale-105"
                >
                    <Info :size="12" />
                </button>
            </PopoverTrigger>
            <InlinePopoverContent
                side="left"
                align="start"
                :side-offset="12"
                class="w-64 rounded-xl border border-border/40 bg-background/96 p-1.5 shadow-cartoon-lg backdrop-blur-xl"
            >
                <ProviderMetadataCard
                    v-for="src in sortedDropdownEntries"
                    :key="getKey(src)"
                    :provider="getId(src)"
                    :display-name="getProviderDisplayName(getId(src))"
                    :is-active="activeSource === getId(src)"
                    :interactive="interactive"
                    :version="'entry_version' in src ? src.entry_version : undefined"
                    :richness-score="providerMetadata.get(getId(src))?.richness_score ?? null"
                    :definition-count="providerMetadata.get(getId(src))?.definition_count ?? null"
                    :fetched-at="providerMetadata.get(getId(src))?.fetched_at ?? null"
                    @click="handleDropdownSelect(getId(src))"
                />
            </InlinePopoverContent>
        </Popover>
    </div>

    <!-- Horizontal layout: providers with info popover (works for 1+ providers) -->
    <Popover v-else-if="showSynthesis || providers.length > 0" v-model:open="popoverOpen">
        <div class="flex items-center">
            <!-- AI Synthesis icon (separate from stack) -->
            <Tooltip v-if="showSynthesis">
                <TooltipTrigger as-child>
                    <button
                        :disabled="!interactive"
                        @click.stop="$emit('select-source', 'synthesis')"
                        :class="[
                            'flex h-10 w-10 items-center justify-center rounded-full border shadow-sm transform-gpu transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-250 ease-apple-spring',
                            activeSource === 'synthesis'
                                ? 'border-amber-500/40 bg-amber-500/12 text-amber-600 dark:border-amber-400/40 dark:text-amber-400 ring-2 ring-amber-500/20'
                                : interactive
                                  ? 'border-border/30 bg-background/96 text-muted-foreground/80 opacity-70 hover:border-border/50 hover:bg-background hover:opacity-100'
                                  : 'cursor-default border-border/20 bg-muted/80 text-muted-foreground/50 opacity-60',
                        ]"
                    >
                        <Wand2 :size="20" />
                    </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" :side-offset="6">
                    AI Synthesis
                </TooltipContent>
            </Tooltip>

            <!-- Vertical divider -->
            <div
                v-if="showSynthesis && providers.length > 0"
                class="mx-1.5 h-7 w-px bg-border/40"
            />

            <!-- Provider icons — each individually clickable to switch, expand on hover -->
            <div
                v-if="providers.length > 0"
                class="group/stack relative isolate flex items-center"
            >
                <!-- Info button — top-left of first provider icon -->
                <PopoverTrigger as-child>
                    <button
                    class="absolute -top-2 -left-2 flex h-6 w-6 items-center justify-center rounded-full border border-border/40 bg-background/96 text-muted-foreground/60 shadow-sm transition-[background-color,color,opacity,transform] duration-200 ease-apple-smooth opacity-0 group-hover/stack:opacity-100 hover:bg-background hover:text-muted-foreground hover:scale-105 z-controls"
                    >
                        <Info :size="14" />
                    </button>
                </PopoverTrigger>

                <Tooltip v-for="(provider, i) in orderedProviders" :key="provider">
                    <TooltipTrigger as-child>
                        <button
                            :disabled="!interactive"
                        @click="$emit('select-source', provider)"
                        :class="[
                            'flex h-10 w-10 items-center justify-center rounded-full border bg-background/96 shadow-sm transform-gpu transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-250 ease-apple-spring',
                            interactive ? 'cursor-pointer hover:-translate-y-0.5 hover:bg-background hover:border-border/50 hover:shadow-md' : 'cursor-default',
                            i > 0 ? '-ml-3 group-hover/stack:translate-x-2 group-hover/stack:scale-105' : '',
                            activeSource === provider
                                ? 'border-primary/40 ring-2 ring-primary/20 bg-primary/10'
                                : 'border-border/30',
                            ]"
                            :style="{ zIndex: orderedProviders.length - i }"
                        >
                            <component
                                :is="getProviderIcon(provider)"
                                :size="20"
                                class="text-muted-foreground"
                            />
                        </button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom" :side-offset="6">
                        {{ getProviderDisplayName(provider) }}
                    </TooltipContent>
                </Tooltip>
            </div>
        </div>

        <!-- Provider metadata dropdown -->
        <InlinePopoverContent
            side="bottom"
            align="end"
            :side-offset="12"
            :collision-padding="16"
            class="z-popover w-64 rounded-xl border border-border/40 bg-popover p-1.5 shadow-xl backdrop-blur-xl"
        >
            <ProviderMetadataCard
                v-for="src in sortedDropdownEntries"
                :key="getKey(src)"
                :provider="getId(src)"
                :display-name="getProviderDisplayName(getId(src))"
                :is-active="activeSource === getId(src)"
                :interactive="interactive"
                :version="'entry_version' in src ? src.entry_version : undefined"
                :richness-score="providerMetadata.get(getId(src))?.richness_score ?? null"
                :definition-count="providerMetadata.get(getId(src))?.definition_count ?? null"
                :fetched-at="providerMetadata.get(getId(src))?.fetched_at ?? null"
                @click="handleDropdownSelect(getId(src))"
            />
        </InlinePopoverContent>
    </Popover>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Wand2, Info } from 'lucide-vue-next';
import { Popover, PopoverTrigger, Tooltip, TooltipTrigger, TooltipContent } from '@mkbabb/glass-ui';
import {
    PopoverContent as InlinePopoverContent,
} from 'reka-ui';
import {
    getProviderIcon,
    getProviderDisplayName,
} from '../../utils/providers';
import ProviderMetadataCard from './ProviderMetadataCard.vue';
import { providersApi, type ProviderEntry } from '@/api/providers';
import type { SourceReference } from '@/types/api';

interface ProviderIconsProps {
    providers: string[];
    activeSource?: string;
    showSynthesis?: boolean;
    interactive?: boolean;
    sourceEntries?: SourceReference[];
    word?: string;
    layout?: 'horizontal' | 'vertical';
}

const props = withDefaults(defineProps<ProviderIconsProps>(), {
    activeSource: 'synthesis',
    showSynthesis: true,
    interactive: true,
    layout: 'horizontal',
});

const emit = defineEmits<{
    'select-source': [source: string];
}>();

// Lazy-fetch provider metadata on popover open
const providerMetadata = ref<Map<string, ProviderEntry>>(new Map());
const metadataLoaded = ref(false);
const popoverOpen = ref(false);

watch(popoverOpen, async (open) => {
    if (!open || metadataLoaded.value || !props.word) return;
    try {
        const entries = await providersApi.getWordProviders(props.word);
        const map = new Map<string, ProviderEntry>();
        for (const e of entries) map.set(e.provider, e);
        providerMetadata.value = map;
        metadataLoaded.value = true;
    } catch {
        // Silently degrade — cards render without richness data
    }
});

// Reset cache when word changes
watch(() => props.word, () => {
    metadataLoaded.value = false;
    providerMetadata.value = new Map();
});

// Select from dropdown and close popover
function handleDropdownSelect(provider: string) {
    emit('select-source', provider);
    popoverOpen.value = false;
}

// Sort providers by richness (richest first) — used for icon stack and dropdown
const richnessSorted = computed(() => {
    const list = [...props.providers];
    if (list.length <= 1 || providerMetadata.value.size === 0) return list;
    return list.sort((a, b) => {
        const ra = providerMetadata.value.get(a)?.richness_score ?? 0;
        const rb = providerMetadata.value.get(b)?.richness_score ?? 0;
        return rb - ra; // descending
    });
});

// Icon stack: stable order by richness — never reorder on active change to prevent flash
const orderedProviders = computed(() => {
    return richnessSorted.value;
});

// Dropdown list: sorted by richness (richest first)
const sortedDropdownEntries = computed(() => {
    const base = props.sourceEntries?.length ? props.sourceEntries : providerFallback.value;
    if (providerMetadata.value.size === 0) return base;
    return [...base].sort((a, b) => {
        const idA = getId(a);
        const idB = getId(b);
        const ra = providerMetadata.value.get(idA)?.richness_score ?? 0;
        const rb = providerMetadata.value.get(idB)?.richness_score ?? 0;
        return rb - ra;
    });
});

// Fallback for when sourceEntries is empty but we have provider strings
const providerFallback = computed(() =>
    props.providers.map(p => ({ id: p }))
);

// Helpers to normalize source entry shape
const getId = (src: SourceReference | { id: string }) =>
    'provider' in src ? src.provider : (src as { id: string }).id;
const getKey = (src: SourceReference | { id: string }) =>
    'entry_id' in src ? src.entry_id : (src as { id: string }).id;
</script>
