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

    <!-- Multiple providers: overlapping stack + inline popover (no portal — stays in card DOM) -->
    <Popover v-else-if="showSynthesis || providers.length > 0">
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

            <!-- Overlapping provider stack — expands on hover, triggers popover on click -->
            <PopoverTrigger as-child>
                <button
                    v-if="providers.length > 0"
                    class="group/stack flex items-center focus:outline-none focus:ring-0"
                    :class="[
                        interactive
                            ? 'cursor-pointer'
                            : 'cursor-default',
                    ]"
                >
                    <div
                        v-for="(provider, i) in orderedProviders"
                        :key="provider"
                        :class="[
                            'flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted/80 shadow-sm transition-all duration-200 ease-apple-spring',
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
                    </div>
                </button>
            </PopoverTrigger>
        </div>

        <!-- Provider selection dropdown — rendered inline (no PopoverPortal) to preserve card hover -->
        <InlinePopoverContent
            side="bottom"
            align="start"
            :side-offset="20"
            class="w-56 rounded-xl border border-border/30 bg-background/92 p-1.5 shadow-lg backdrop-blur-md"
        >
            <div
                v-for="src in (sourceEntries?.length ? sourceEntries : providerFallback)"
                :key="getKey(src)"
                class="flex items-center gap-3 rounded-lg px-2.5 py-2 transition-colors duration-150"
                :class="[
                    interactive ? 'cursor-pointer hover:bg-muted/60' : 'cursor-default',
                    activeSource === getId(src)
                        ? 'bg-primary/10 font-medium text-foreground'
                        : 'text-foreground/80',
                ]"
                @click="$emit('select-source', getId(src))"
            >
                <component
                    :is="getProviderIcon(getId(src))"
                    :size="16"
                    class="flex-shrink-0"
                    :class="activeSource === getId(src) ? 'text-foreground' : 'text-muted-foreground'"
                />
                <span class="text-sm flex-1">
                    {{ getProviderDisplayName(getId(src)) }}
                </span>
                <span
                    v-if="'entry_version' in src && src.entry_version"
                    class="font-mono text-xs text-muted-foreground/60"
                >v{{ src.entry_version }}</span>
                <div
                    v-if="activeSource === getId(src)"
                    class="h-1.5 w-1.5 rounded-full bg-primary flex-shrink-0"
                />
            </div>
        </InlinePopoverContent>
    </Popover>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Wand2 } from 'lucide-vue-next';
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
import type { SourceReference } from '@/types/api';

interface ProviderIconsProps {
    providers: string[];
    activeSource?: string;
    showSynthesis?: boolean;
    interactive?: boolean;
    sourceEntries?: SourceReference[];
}

const props = withDefaults(defineProps<ProviderIconsProps>(), {
    activeSource: 'synthesis',
    showSynthesis: true,
    interactive: true,
});

defineEmits<{
    'select-source': [source: string];
}>();

// Reorder providers so the active source is always first in the stack
const orderedProviders = computed(() => {
    const list = props.providers;
    if (!list || list.length <= 1) return list;
    const active = props.activeSource;
    if (!active || active === 'synthesis' || list[0] === active) return list;
    return [active, ...list.filter(p => p !== active)];
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
