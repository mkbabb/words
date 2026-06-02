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
                        'flex h-10 w-10 items-center justify-center rounded-full border shadow-cartoon-sm transform-gpu transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-fast ease-spring-snappy',
                        activeSource === 'synthesis'
                            ? 'border-[var(--color-gold)]/40 bg-[var(--color-gold)]/12 text-[var(--color-gold)] ring-2 ring-[var(--color-gold)]/20'
                            : interactive
                              ? 'border-border/40 bg-background/96 text-muted-foreground/80 opacity-70 hover:border-border/60 hover:bg-background hover:opacity-100 hover:-translate-y-0.5 scale-on-hover'
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
                        'flex h-10 w-10 items-center justify-center rounded-full border bg-background/96 shadow-cartoon-sm transform-gpu transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-fast ease-spring-snappy',
                        interactive ? 'cursor-pointer hover:-translate-y-0.5 scale-on-hover hover:bg-background hover:shadow-cartoon-md' : 'cursor-default',
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
                    class="flex h-6 w-6 items-center justify-center rounded-full text-muted-foreground/40 transition-[background-color,color,transform] duration-fast ease-spring-smooth hover:bg-background/90 hover:text-muted-foreground scale-on-hover"
                >
                    <Info :size="12" />
                </button>
            </PopoverTrigger>
            <PopoverContent
                :portal="false"
                side="left"
                align="start"
                :side-offset="12"
                class="w-64 p-1.5 shadow-cartoon-lg"
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
            </PopoverContent>
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
                            'flex h-10 w-10 items-center justify-center rounded-full border shadow-cartoon-sm transform-gpu transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-fast ease-spring-snappy',
                            activeSource === 'synthesis'
                                ? 'border-[var(--color-gold)]/40 bg-[var(--color-gold)]/12 text-[var(--color-gold)] ring-2 ring-[var(--color-gold)]/20'
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

            <!-- Provider icons — stacked, expand on hover -->
            <StackedIconGroup
                v-if="providers.length > 0"
                :items="orderedProviders"
                :max-visible="3"
                size="lg"
                :key-fn="(p: string) => p"
            >
                <!-- @vue-ignore -->
                <template #icon="{ item: provider }: { item: string }">
                    <Tooltip>
                        <TooltipTrigger as-child>
                            <button
                                :disabled="!interactive"
                                @click="$emit('select-source', provider)"
                                :class="[
                                    'flex h-10 w-10 items-center justify-center rounded-full border bg-background/96 shadow-cartoon-sm',
                                    'transform-gpu transition-[background-color,border-color,color,box-shadow,transform,opacity] duration-fast ease-spring-snappy',
                                    interactive ? 'cursor-pointer hover:-translate-y-0.5 hover:bg-background hover:border-border/50 hover:shadow-cartoon-md' : 'cursor-default',
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
                        <TooltipContent side="bottom" :side-offset="6">
                            {{ getProviderDisplayName(provider) }}
                        </TooltipContent>
                    </Tooltip>
                </template>

                <!-- @vue-ignore -->
                <template #info>
                    <PopoverTrigger as-child>
                        <button
                            class="absolute -top-2 -left-2 flex h-6 w-6 items-center justify-center rounded-full border border-border/40 bg-background/96 text-muted-foreground/60 shadow-cartoon-sm transition-[background-color,color,opacity,transform] duration-fast ease-spring-smooth opacity-0 group-hover/stack:opacity-100 hover:bg-background hover:text-muted-foreground scale-on-hover z-controls"
                        >
                            <Info :size="14" />
                        </button>
                    </PopoverTrigger>
                </template>
            </StackedIconGroup>
        </div>

        <!-- Provider metadata dropdown -->
        <PopoverContent
            :portal="false"
            side="bottom"
            align="end"
            :side-offset="12"
            :collision-padding="16"
            class="w-64 p-1.5 shadow-cartoon-lg"
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
        </PopoverContent>
    </Popover>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { Wand2, Info } from '@lucide/vue';
import { Popover, PopoverTrigger, PopoverContent } from '@mkbabb/glass-ui/popover';
import { Tooltip, TooltipTrigger, TooltipContent } from '@mkbabb/glass-ui/tooltip';
import { StackedIconGroup } from '@mkbabb/glass-ui/stacked-icons';
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
