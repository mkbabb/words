<template>
    <!-- Single provider: direct click, no popover -->
    <div
        v-if="(showSynthesis || providers.length > 0) && providers.length <= 1"
        class="flex items-center"
    >
        <!-- AI Synthesis icon -->
        <button
            v-if="showSynthesis"
            :title="'AI Synthesis'"
            :disabled="!interactive"
            @click="$emit('select-source', 'synthesis')"
            :class="[
                'flex h-7 w-7 items-center justify-center rounded-full border shadow-sm transition-all duration-200',
                activeSource === 'synthesis'
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:border-amber-400/40 dark:text-amber-400'
                    : interactive
                      ? 'border-border/50 bg-background text-muted-foreground opacity-60 hover:border-border hover:opacity-100'
                      : 'cursor-default border-border/50 bg-background text-muted-foreground/60 opacity-60',
            ]"
        >
            <Wand2 :size="14" />
        </button>

        <!-- Divider between AI and single provider -->
        <div
            v-if="showSynthesis && providers.length === 1"
            class="mx-1.5 h-7 w-[2px] bg-border/70"
        />

        <!-- Single provider icon — direct click -->
        <button
            v-if="providers.length === 1"
            :title="getProviderDisplayName(providers[0])"
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
    </div>

    <!-- Multiple providers: overlapping stack + popover -->
    <Popover v-else-if="showSynthesis || providers.length > 0">
        <div class="flex items-center">
            <!-- AI Synthesis icon (separate from stack) -->
            <button
                v-if="showSynthesis"
                :title="'AI Synthesis'"
                :disabled="!interactive"
                @click="$emit('select-source', 'synthesis')"
                :class="[
                    'flex h-7 w-7 items-center justify-center rounded-full border shadow-sm transition-all duration-200',
                    activeSource === 'synthesis'
                        ? 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:border-amber-400/40 dark:text-amber-400'
                        : interactive
                          ? 'border-border/50 bg-background text-muted-foreground opacity-60 hover:border-border hover:opacity-100'
                          : 'cursor-default border-border/50 bg-background text-muted-foreground/60 opacity-60',
                ]"
            >
                <Wand2 :size="14" />
            </button>

            <!-- Vertical divider -->
            <div
                v-if="showSynthesis && providers.length > 0"
                class="mx-1.5 h-7 w-[2px] bg-border/70"
            />

            <!-- Overlapping provider stack (triggers popover) -->
            <PopoverTrigger as-child>
                <button
                    v-if="providers.length > 0"
                    class="flex items-center focus:outline-none focus:ring-0"
                    :class="[
                        interactive
                            ? 'cursor-pointer'
                            : 'cursor-default',
                    ]"
                >
                    <div
                        v-for="(provider, i) in providers"
                        :key="provider"
                        :class="[
                            'flex h-7 w-7 items-center justify-center rounded-full border-2 border-background bg-muted/80 shadow-sm transition-all duration-200',
                            i > 0 ? '-ml-2' : '',
                            activeSource === provider
                                ? 'ring-2 ring-primary/30'
                                : '',
                        ]"
                        :style="{ zIndex: providers.length - i }"
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

        <!-- Glassmorphism detail card -->
        <PopoverContent
            side="bottom"
            align="start"
            :side-offset="8"
            class="w-64 rounded-xl border border-border/30 bg-background/80 p-3 shadow-xl backdrop-blur-xl"
        >
            <div
                v-for="src in sourceEntries"
                :key="src.entry_id"
                class="flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2 transition-colors duration-150 hover:bg-muted/50"
                @click="$emit('select-source', src.provider)"
            >
                <component
                    :is="getProviderIcon(src.provider)"
                    :size="18"
                    class="flex-shrink-0 text-muted-foreground"
                />
                <div class="flex-1">
                    <span class="text-sm font-medium">{{
                        getProviderDisplayName(src.provider)
                    }}</span>
                    <span
                        v-if="src.entry_version"
                        class="ml-1.5 font-mono text-xs text-muted-foreground"
                        >v{{ src.entry_version }}</span
                    >
                </div>
            </div>
            <!-- Fallback when no sourceEntries but providers exist -->
            <template v-if="!sourceEntries?.length">
                <div
                    v-for="provider in providers"
                    :key="provider"
                    class="flex cursor-pointer items-center gap-3 rounded-lg px-2 py-2 transition-colors duration-150 hover:bg-muted/50"
                    @click="$emit('select-source', provider)"
                >
                    <component
                        :is="getProviderIcon(provider)"
                        :size="18"
                        class="flex-shrink-0 text-muted-foreground"
                    />
                    <span class="text-sm font-medium">{{
                        getProviderDisplayName(provider)
                    }}</span>
                </div>
            </template>
        </PopoverContent>
    </Popover>
</template>

<script setup lang="ts">
import { Wand2 } from 'lucide-vue-next';
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from '@/components/ui/popover';
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

withDefaults(defineProps<ProviderIconsProps>(), {
    activeSource: 'synthesis',
    showSynthesis: true,
    interactive: true,
});

defineEmits<{
    'select-source': [source: string];
}>();
</script>
