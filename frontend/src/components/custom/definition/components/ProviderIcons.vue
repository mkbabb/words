<template>
    <!-- Single provider: direct click, no popover -->
    <div
        v-if="(showSynthesis || providers.length > 0) && providers.length <= 1"
        class="flex items-center"
    >
        <!-- AI Synthesis icon -->
        <Tooltip v-if="showSynthesis">
            <TooltipTrigger as-child>
                <button
                    :disabled="!interactive"
                    @click="$emit('select-source', 'synthesis')"
                    :class="[
                        'flex h-7 w-7 items-center justify-center rounded-full border shadow-sm transition-all duration-200',
                        activeSource === 'synthesis'
                            ? 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:border-amber-400/40 dark:text-amber-400 ring-2 ring-amber-500/20'
                            : interactive
                              ? 'border-border/50 bg-background text-muted-foreground opacity-60 hover:border-border hover:opacity-100'
                              : 'cursor-default border-border/50 bg-background text-muted-foreground/60 opacity-60',
                    ]"
                >
                    <Wand2 :size="14" />
                </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" :side-offset="6">
                AI Synthesis
            </TooltipContent>
        </Tooltip>

        <!-- Divider between AI and single provider -->
        <div
            v-if="showSynthesis && providers.length === 1"
            class="mx-1.5 h-5 w-px bg-border/50"
        />

        <!-- Single provider icon — direct click -->
        <Tooltip v-if="providers.length === 1">
            <TooltipTrigger as-child>
                <button
                    :disabled="!interactive"
                    @click="$emit('select-source', providers[0])"
                    :class="[
                        'flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted/80 shadow-sm transition-all duration-200',
                        interactive ? 'cursor-pointer hover:bg-muted' : 'cursor-default',
                        activeSource === providers[0] ? 'ring-2 ring-primary/30' : '',
                    ]"
                >
                    <component
                        :is="getProviderIcon(providers[0])"
                        :size="14"
                        class="text-muted-foreground"
                    />
                </button>
            </TooltipTrigger>
            <TooltipContent side="bottom" :side-offset="6">
                {{ getProviderDisplayName(providers[0]) }}
            </TooltipContent>
        </Tooltip>
    </div>

    <!-- Multiple providers: individually clickable icons + info popover -->
    <Popover v-else-if="showSynthesis || providers.length > 0" v-model:open="popoverOpen">
        <div class="flex items-center">
            <!-- AI Synthesis icon (separate from stack) -->
            <Tooltip v-if="showSynthesis">
                <TooltipTrigger as-child>
                    <button
                        :disabled="!interactive"
                        @click.stop="$emit('select-source', 'synthesis')"
                        :class="[
                            'flex h-7 w-7 items-center justify-center rounded-full border shadow-sm transition-all duration-200',
                            activeSource === 'synthesis'
                                ? 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:border-amber-400/40 dark:text-amber-400 ring-2 ring-amber-500/20'
                                : interactive
                                  ? 'border-border/50 bg-background text-muted-foreground opacity-60 hover:border-border hover:opacity-100'
                                  : 'cursor-default border-border/50 bg-background text-muted-foreground/60 opacity-60',
                        ]"
                    >
                        <Wand2 :size="14" />
                    </button>
                </TooltipTrigger>
                <TooltipContent side="bottom" :side-offset="6">
                    AI Synthesis
                </TooltipContent>
            </Tooltip>

            <!-- Vertical divider -->
            <div
                v-if="showSynthesis && providers.length > 0"
                class="mx-1.5 h-5 w-px bg-border/50"
            />

            <!-- Provider icons — each individually clickable to switch, expand on hover -->
            <div
                v-if="providers.length > 0"
                class="group/stack relative flex items-center"
            >
                <!-- Info button — floats above the icon stack -->
                <PopoverTrigger as-child>
                    <button
                        class="absolute -top-3.5 left-1/2 -translate-x-1/2 flex h-4 w-4 items-center justify-center rounded-full text-muted-foreground/40 transition-all duration-150 opacity-0 group-hover/stack:opacity-100 hover:text-muted-foreground hover:bg-muted/60 z-10"
                    >
                        <Info :size="10" />
                    </button>
                </PopoverTrigger>

                <Tooltip v-for="(provider, i) in orderedProviders" :key="provider">
                    <TooltipTrigger as-child>
                        <button
                            :disabled="!interactive"
                            @click="$emit('select-source', provider)"
                            :class="[
                                'flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted/80 shadow-sm transition-all duration-200 ease-apple-spring',
                                interactive ? 'cursor-pointer hover:bg-muted' : 'cursor-default',
                                i > 0 ? '-ml-2 group-hover/stack:ml-0.5' : '',
                                activeSource === provider
                                    ? 'ring-2 ring-primary/30 bg-muted'
                                    : '',
                            ]"
                            :style="{ zIndex: orderedProviders.length - i }"
                        >
                            <component
                                :is="getProviderIcon(provider)"
                                :size="14"
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
            align="start"
            :side-offset="20"
            class="w-64 rounded-xl border border-border/40 bg-popover p-1.5 shadow-lg backdrop-blur-md"
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
import {
    Popover,
    PopoverTrigger,
} from '@/components/ui/popover';
import {
    PopoverContent as InlinePopoverContent,
} from 'reka-ui';
import {
    Tooltip,
    TooltipTrigger,
    TooltipContent,
} from '@/components/ui/tooltip';
import {
    getProviderIcon,
    getProviderDisplayName,
} from '../utils/providers';
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
}

const props = withDefaults(defineProps<ProviderIconsProps>(), {
    activeSource: 'synthesis',
    showSynthesis: true,
    interactive: true,
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

// Icon stack: active source shown first (z-order), rest by richness
const orderedProviders = computed(() => {
    const list = richnessSorted.value;
    if (!list || list.length <= 1) return list;
    const active = props.activeSource;
    if (!active || active === 'synthesis' || list[0] === active) return list;
    return [active, ...list.filter(p => p !== active)];
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
