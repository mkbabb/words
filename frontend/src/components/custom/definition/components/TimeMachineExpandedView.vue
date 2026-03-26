<template>
    <div class="flex h-full w-full max-w-3xl flex-col">
        <!-- Back button header -->
        <div class="mb-3 flex items-center gap-3">
            <button
                class="flex h-8 items-center gap-1.5 rounded-lg border border-border/40 bg-background/80 px-3 text-xs text-muted-foreground backdrop-blur-sm transition-colors hover:bg-background/95 hover:text-foreground"
                @click="$emit('collapse')"
            >
                <ChevronLeft :size="14" />
                Back
            </button>
            <Badge variant="outline" class="font-mono text-xs">
                v{{ version.version }}
            </Badge>
            <Badge
                v-if="version.is_latest"
                variant="secondary"
                class="text-micro"
            >
                Latest
            </Badge>
            <span class="text-xs text-muted-foreground">
                {{ formatDate(version.created_at) }}
            </span>
            <span
                v-if="diffFields.size > 0"
                class="flex items-center gap-1.5 text-micro font-medium text-amber-500/80"
            >
                <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
                {{ diffFields.size }} field{{ diffFields.size !== 1 ? 's' : '' }} changed
            </span>
        </div>

        <!-- Scrollable entry content — uses the same renderer as DefinitionDisplay -->
        <div
            class="flex-1 overflow-y-auto rounded-xl border border-border/30 bg-background/80 shadow-2xl shadow-cartoon-lg backdrop-blur-xl scrollbar-thin"
        >
            <DefinitionContentRenderer
                v-if="hydratedEntry"
                :entry="hydratedEntry"
                :diff-fields="diffFields"
                :text-changes="textChanges"
            />
            <div v-else class="flex items-center justify-center py-16 text-sm text-muted-foreground/50">
                Loading version content...
            </div>
        </div>

        <!-- Action bar -->
        <div class="mt-3 flex items-center justify-between">
            <!-- Version metadata -->
            <div class="flex items-center gap-3 text-micro text-muted-foreground/50">
                <span>Hash: {{ version.data_hash?.slice(0, 12) }}</span>
                <span>{{ version.storage_mode === 'snapshot' ? 'Full snapshot' : 'Delta' }}</span>
            </div>

            <Button
                v-if="isAdmin && !isCurrentVersion"
                variant="ghost"
                size="sm"
                class="h-7 gap-1.5 text-xs text-orange-500 hover:text-orange-600"
                :disabled="rollingBack"
                @click="$emit('rollback')"
            >
                <RotateCcw :size="12" />
                {{ rollingBack ? 'Rolling back...' : 'Rollback to this version' }}
            </Button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ChevronLeft, RotateCcw } from 'lucide-vue-next';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import DefinitionContentRenderer from './content/DefinitionContentRenderer.vue';
import { useAuthStore } from '@/stores/auth';
import type { VersionSummary } from '@/types/api';
import type { SynthesizedDictionaryEntry } from '@/types';
import type { TextChange } from '../composables/useTimeMachine';

interface Props {
    version: VersionSummary;
    hydratedEntry: SynthesizedDictionaryEntry | null;
    isCurrentVersion: boolean;
    rollingBack: boolean;
    diffFields: Set<string>;
    textChanges: Map<string, TextChange[]>;
}

defineProps<Props>();

defineEmits<{
    collapse: [];
    rollback: [];
}>();

const auth = useAuthStore();
const isAdmin = auth.isAdmin;

function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}
</script>
