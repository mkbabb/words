<template>
    <div
        v-if="showSynthesis || providers.length > 0"
        class="ml-3 flex items-center gap-1"
    >
        <!-- AI Synthesis source -->
        <button
            v-if="showSynthesis"
            :title="'AI Synthesis'"
            @click="$emit('select-source', 'synthesis')"
            :class="[
                'flex h-7 w-7 items-center justify-center rounded-full border shadow-sm transition-all duration-200',
                activeSource === 'synthesis'
                    ? 'border-amber-500/40 bg-amber-500/10 text-amber-600 dark:border-amber-400/40 dark:text-amber-400'
                    : 'border-border/50 bg-background text-muted-foreground opacity-60 hover:border-border hover:opacity-100',
            ]"
        >
            <Wand2 :size="14" />
        </button>

        <!-- Provider source icons -->
        <button
            v-for="provider in providers"
            :key="provider"
            :title="getProviderDisplayName(provider)"
            @click="$emit('select-source', provider)"
            :class="[
                'flex h-7 w-7 items-center justify-center rounded-full border shadow-sm transition-all duration-200',
                activeSource === provider
                    ? 'border-primary/40 bg-primary/10 text-foreground'
                    : 'border-border/50 bg-background text-muted-foreground opacity-60 hover:border-border hover:opacity-100',
            ]"
        >
            <component :is="getProviderIcon(provider)" :size="16" />
        </button>
    </div>
</template>

<script setup lang="ts">
import { Wand2 } from 'lucide-vue-next';
import {
    getProviderIcon,
    getProviderDisplayName,
} from '../utils/providers';

interface ProviderIconsProps {
    providers: string[];
    activeSource?: string;
    showSynthesis?: boolean;
}

withDefaults(defineProps<ProviderIconsProps>(), {
    activeSource: 'synthesis',
    showSynthesis: true,
});

defineEmits<{
    'select-source': [source: string];
}>();
</script>
