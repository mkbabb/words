<template>
    <div
        v-if="metadata"
        class="space-y-1 rounded-md border border-border/20 bg-muted/10 px-2 py-1.5"
    >
        <!-- Operation type + user -->
        <div class="flex items-center gap-1.5 text-[10px]">
            <Badge variant="outline" class="h-4 px-1 text-[9px] font-medium">
                {{ operationLabel }}
            </Badge>
            <span v-if="metadata.username" class="text-muted-foreground">
                by {{ metadata.username }}
            </span>
        </div>

        <!-- Change reason -->
        <p
            v-if="metadata.change_reason"
            class="text-[10px] text-muted-foreground/80 italic"
        >
            {{ metadata.change_reason }}
        </p>

        <!-- Synthesis audit -->
        <div
            v-if="metadata.synthesis_audit"
            class="flex flex-wrap gap-1.5 text-[9px] text-muted-foreground/60"
        >
            <span class="font-mono">{{ metadata.synthesis_audit.model_name }}</span>
            <span v-if="metadata.synthesis_audit.total_tokens">
                {{ metadata.synthesis_audit.total_tokens.toLocaleString() }} tok
            </span>
            <span>
                {{ metadata.synthesis_audit.definitions_input }}&rarr;{{ metadata.synthesis_audit.definitions_output }} defs
            </span>
            <span v-if="metadata.synthesis_audit.dedup_removed > 0">
                &minus;{{ metadata.synthesis_audit.dedup_removed }} dedup
            </span>
        </div>

        <!-- Field-level changes -->
        <div
            v-if="metadata.field_changes?.length"
            class="flex flex-wrap gap-1"
        >
            <span
                v-for="(fc, i) in visibleChanges"
                :key="i"
                class="rounded px-1 py-0.5 text-[9px] font-mono"
                :class="changeTypeClass(fc.change_type)"
            >
                {{ changePrefix(fc.change_type) }}{{ fc.field_path }}
            </span>
            <span
                v-if="overflowCount > 0"
                class="text-[9px] text-muted-foreground/50"
            >
                +{{ overflowCount }} more
            </span>
        </div>
    </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Badge } from '@/components/ui/badge';
import type { EditMetadataSummary } from '@/types/api';

const MAX_VISIBLE_CHANGES = 5;

const OPERATION_LABELS: Record<string, string> = {
    ai_synthesis: 'AI Synthesis',
    manual_edit: 'Manual Edit',
    provider_refresh: 'Provider Refresh',
    rollback: 'Rollback',
    component_regeneration: 'Regeneration',
    auto_correct: 'Auto-correct',
    import: 'Import',
};

const CHANGE_TYPE_CLASSES: Record<string, string> = {
    added: 'bg-green-500/10 text-green-600 dark:text-green-400',
    removed: 'bg-red-500/10 text-red-600 dark:text-red-400',
    modified: 'bg-blue-500/10 text-blue-600 dark:text-blue-400',
};

const props = defineProps<{
    metadata: EditMetadataSummary | null | undefined;
}>();

const operationLabel = computed(() =>
    OPERATION_LABELS[props.metadata?.operation_type ?? ''] ??
    (props.metadata?.operation_type ?? '').replace(/_/g, ' '),
);

const visibleChanges = computed(() =>
    props.metadata?.field_changes?.slice(0, MAX_VISIBLE_CHANGES) ?? [],
);

const overflowCount = computed(() =>
    Math.max(0, (props.metadata?.field_changes?.length ?? 0) - MAX_VISIBLE_CHANGES),
);

function changeTypeClass(type: string): string {
    return CHANGE_TYPE_CLASSES[type] ?? CHANGE_TYPE_CLASSES.modified;
}

function changePrefix(type: string): string {
    return type === 'added' ? '+' : type === 'removed' ? '-' : '~';
}
</script>
