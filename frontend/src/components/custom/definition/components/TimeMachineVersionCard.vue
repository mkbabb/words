<template>
    <div class="w-full max-w-lg">
        <Transition
            :name="direction === 'forward' ? 'slide-left' : 'slide-right'"
            mode="out-in"
        >
            <div
                v-if="version"
                :key="version.version"
                class="rounded-xl border border-border/30 bg-background/80 p-6 shadow-2xl shadow-cartoon-lg backdrop-blur-xl"
            >
                <!-- Header -->
                <div class="flex items-center gap-2">
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
                    <Badge v-if="isCurrentVersion" class="text-micro">
                        Current
                    </Badge>
                    <span class="ml-auto text-xs text-muted-foreground">
                        {{ formatDate(version.created_at) }}
                    </span>
                </div>

                <!-- Loading state -->
                <div v-if="detailLoading" class="mt-4 space-y-3">
                    <div class="h-4 w-32 animate-pulse rounded bg-muted" />
                    <div class="h-4 w-48 animate-pulse rounded bg-muted" />
                    <div class="h-16 w-full animate-pulse rounded bg-muted" />
                </div>

                <!-- Detail content (snapshot) -->
                <template v-else-if="content">
                    <!-- Stats row -->
                    <div class="mt-4 flex items-center gap-3 text-xs">
                        <FieldWithDiff field="definition_ids" :diff-fields="diffFields">
                            <div class="flex items-center gap-1.5 text-muted-foreground">
                                <BookOpen :size="12" />
                                <span class="font-medium text-foreground/80">
                                    {{ definitionCount }}
                                </span>
                                definitions
                            </div>
                        </FieldWithDiff>

                        <!-- Provider icons -->
                        <FieldWithDiff field="source_entries" :diff-fields="diffFields">
                            <ProviderIcons
                                v-if="sourceProviders.length"
                                :providers="sourceProviders"
                                :show-synthesis="!!content.model_info"
                                :interactive="false"
                            />
                        </FieldWithDiff>
                    </div>

                    <!-- Etymology snippet -->
                    <FieldWithDiff field="etymology" :diff-fields="diffFields" class="mt-3">
                        <div v-if="content.etymology?.text" class="border-t border-border/15 pt-3">
                            <p class="line-clamp-3 text-xs italic text-foreground/50">
                                {{ content.etymology.text }}
                            </p>
                        </div>
                    </FieldWithDiff>

                    <!-- Languages -->
                    <FieldWithDiff field="languages" :diff-fields="diffFields" class="mt-2">
                        <div v-if="content.languages?.length" class="text-xs text-muted-foreground">
                            Languages: {{ content.languages.join(', ') }}
                        </div>
                    </FieldWithDiff>

                    <!-- Model info -->
                    <FieldWithDiff field="model_info" :diff-fields="diffFields" class="mt-2">
                        <div
                            v-if="content.model_info"
                            class="flex items-center gap-3 text-micro text-muted-foreground"
                        >
                            <span class="font-mono font-medium text-foreground/60">
                                {{ content.model_info.name ?? content.model_info.model }}
                            </span>
                            <span v-if="content.model_info.total_tokens">
                                {{ content.model_info.total_tokens.toLocaleString() }} tokens
                            </span>
                        </div>
                    </FieldWithDiff>

                    <!-- Edit metadata (who/what/why) -->
                    <EditMetadataBlock
                        v-if="version.edit_metadata"
                        :metadata="version.edit_metadata"
                        class="mt-2"
                    />

                    <!-- Storage mode -->
                    <div class="mt-2 text-micro text-muted-foreground/50">
                        {{ version.storage_mode === 'snapshot' ? 'Full snapshot' : 'Delta' }}
                        · {{ version.data_hash?.slice(0, 8) }}
                    </div>

                    <!-- Diff summary -->
                    <div
                        v-if="diffFields.size > 0"
                        class="mt-2 space-y-1 rounded-lg border border-amber-500/20 bg-amber-500/[0.04] p-2"
                    >
                        <div class="flex items-center gap-1.5 text-micro font-medium text-amber-600 dark:text-amber-400">
                            <span class="inline-block h-1.5 w-1.5 rounded-full bg-amber-500" />
                            {{ diffFields.size }} field{{ diffFields.size !== 1 ? 's' : '' }} changed
                        </div>
                        <div class="flex flex-wrap gap-1">
                            <span
                                v-for="field in [...diffFields]"
                                :key="field"
                                class="rounded bg-amber-500/10 px-1.5 py-0.5 font-mono text-micro text-amber-600 dark:text-amber-400"
                            >
                                {{ field }}
                            </span>
                        </div>
                    </div>
                </template>

                <!-- No detail yet -->
                <div v-else class="mt-4 text-xs text-muted-foreground/50">
                    Select a version to view details
                </div>

                <!-- Action buttons -->
                <div class="mt-4 flex items-center gap-2 border-t border-border/20 pt-4">
                    <Button
                        v-if="content"
                        variant="outline"
                        size="sm"
                        class="h-7 gap-1.5 text-xs"
                        @click="$emit('expand')"
                    >
                        <Maximize2 :size="12" />
                        View Full Entry
                    </Button>

                    <Button
                        v-if="isAdmin && !isCurrentVersion"
                        variant="ghost"
                        size="sm"
                        class="h-7 gap-1.5 text-xs text-orange-500 hover:text-orange-600"
                        :disabled="rollingBack"
                        @click="$emit('rollback')"
                    >
                        <RotateCcw :size="12" />
                        {{ rollingBack ? 'Rolling back...' : 'Rollback' }}
                    </Button>
                </div>
            </div>
        </Transition>
    </div>
</template>

<script setup lang="ts">
import { computed, h, type FunctionalComponent } from 'vue';
import { BookOpen, Maximize2, RotateCcw } from 'lucide-vue-next';
import { Badge, Button } from '@mkbabb/glass-ui';
import ProviderIcons from './metadata/ProviderIcons.vue';
import EditMetadataBlock from './editing/EditMetadataBlock.vue';
import { useAuthStore } from '@/stores/auth';
import type { VersionSummary, VersionDetailResponse } from '@/types/api';

interface Props {
    version: VersionSummary | null;
    detail: VersionDetailResponse | null;
    detailLoading: boolean;
    rollingBack: boolean;
    isCurrentVersion: boolean;
    direction: 'forward' | 'backward';
    diffFields: Set<string>;
}

const props = defineProps<Props>();

defineEmits<{
    rollback: [];
    expand: [];
}>();

const auth = useAuthStore();
const isAdmin = auth.isAdmin;

const content = computed(() => props.detail?.content ?? null);

const definitionCount = computed((): number => {
    if (!content.value) return 0;
    return (content.value.definition_ids?.length as number) ?? 0;
});

const sourceProviders = computed((): string[] => {
    if (!content.value?.source_entries) return [];
    return [
        ...new Set(
            (content.value.source_entries as Array<{ provider: string }>).map(
                (s) => s.provider
            )
        ),
    ];
});

function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

// Inline functional component: wraps content with a diff indicator dot
const FieldWithDiff: FunctionalComponent<
    { field: string; diffFields: Set<string>; class?: string },
    {},
    { default: () => any }
> = (props, { slots }) => {
    const changed = props.diffFields.has(props.field);
    return h(
        'div',
        { class: ['relative', props.class] },
        [
            slots.default?.(),
            changed
                ? h('div', {
                      class: 'absolute -top-1 -right-1 h-2 w-2 rounded-full bg-amber-400 ring-2 ring-background',
                      title: `${props.field} changed`,
                  })
                : null,
        ]
    );
};
FieldWithDiff.props = ['field', 'diffFields', 'class'];
</script>

<style scoped>
.slide-left-enter-active {
    transition: all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.slide-left-leave-active {
    transition: all 200ms cubic-bezier(0.6, -0.28, 0.735, 0.045);
}
.slide-left-enter-from {
    opacity: 0;
    transform: translateX(60px) scale(0.95);
}
.slide-left-leave-to {
    opacity: 0;
    transform: translateX(-60px) scale(0.95);
}

.slide-right-enter-active {
    transition: all 400ms cubic-bezier(0.175, 0.885, 0.32, 1.275);
}
.slide-right-leave-active {
    transition: all 200ms cubic-bezier(0.6, -0.28, 0.735, 0.045);
}
.slide-right-enter-from {
    opacity: 0;
    transform: translateX(-60px) scale(0.95);
}
.slide-right-leave-to {
    opacity: 0;
    transform: translateX(60px) scale(0.95);
}
</style>
