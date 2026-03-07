<template>
    <div class="space-y-3">
        <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold">Version Diff</h3>
            <button
                @click="$emit('close')"
                class="rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
            >
                <X :size="16" />
            </button>
        </div>

        <!-- Version selectors -->
        <div class="flex items-center gap-2 text-sm">
            <select
                v-model="fromVersion"
                class="rounded border border-border bg-background px-2 py-1 text-sm"
            >
                <option
                    v-for="v in versions"
                    :key="v.version"
                    :value="v.version"
                >
                    v{{ v.version }}
                </option>
            </select>
            <span class="text-muted-foreground">&rarr;</span>
            <select
                v-model="toVersion"
                class="rounded border border-border bg-background px-2 py-1 text-sm"
            >
                <option
                    v-for="v in versions"
                    :key="v.version"
                    :value="v.version"
                >
                    v{{ v.version }}
                </option>
            </select>
            <button
                @click="loadDiff"
                :disabled="loading || fromVersion === toVersion"
                class="rounded bg-primary px-3 py-1 text-sm text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
                Compare
            </button>
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="space-y-2">
            <div
                v-for="i in 3"
                :key="i"
                class="h-8 animate-pulse rounded bg-muted"
            />
        </div>

        <!-- No diff loaded -->
        <div
            v-else-if="!diff"
            class="py-4 text-center text-sm text-muted-foreground"
        >
            Select two versions and click Compare.
        </div>

        <!-- No changes -->
        <div
            v-else-if="Object.keys(diff).length === 0"
            class="py-4 text-center text-sm text-muted-foreground"
        >
            No differences between these versions.
        </div>

        <!-- Diff display -->
        <div v-else class="max-h-80 space-y-2 overflow-y-auto">
            <!-- Values Changed -->
            <div v-if="diff.values_changed" class="space-y-1">
                <h4
                    class="text-xs font-semibold text-muted-foreground uppercase"
                >
                    Changed
                </h4>
                <div
                    v-for="(change, path) in diff.values_changed"
                    :key="String(path)"
                    class="rounded border border-border p-2 text-xs"
                >
                    <div class="mb-1 font-mono text-muted-foreground">
                        {{ formatPath(String(path)) }}
                    </div>
                    <div class="flex flex-col gap-1">
                        <div
                            class="rounded bg-red-500/10 px-2 py-0.5 text-red-600 line-through dark:text-red-400"
                        >
                            {{ truncateValue(change.old_value) }}
                        </div>
                        <div
                            class="rounded bg-green-500/10 px-2 py-0.5 text-green-600 dark:text-green-400"
                        >
                            {{ truncateValue(change.new_value) }}
                        </div>
                    </div>
                </div>
            </div>

            <!-- Items Added -->
            <div v-if="diff.dictionary_item_added" class="space-y-1">
                <h4
                    class="text-xs font-semibold text-muted-foreground uppercase"
                >
                    Added
                </h4>
                <div
                    v-for="(value, path) in diff.dictionary_item_added"
                    :key="String(path)"
                    class="rounded border border-green-500/30 bg-green-500/5 p-2 text-xs"
                >
                    <span class="font-mono text-muted-foreground">{{
                        formatPath(String(path))
                    }}</span>
                    <span class="ml-2 text-green-600 dark:text-green-400">{{
                        truncateValue(value)
                    }}</span>
                </div>
            </div>

            <!-- Items Removed -->
            <div v-if="diff.dictionary_item_removed" class="space-y-1">
                <h4
                    class="text-xs font-semibold text-muted-foreground uppercase"
                >
                    Removed
                </h4>
                <div
                    v-for="(value, path) in diff.dictionary_item_removed"
                    :key="String(path)"
                    class="rounded border border-red-500/30 bg-red-500/5 p-2 text-xs"
                >
                    <span class="font-mono text-muted-foreground">{{
                        formatPath(String(path))
                    }}</span>
                    <span
                        class="ml-2 text-red-600 line-through dark:text-red-400"
                        >{{ truncateValue(value) }}</span
                    >
                </div>
            </div>

            <!-- Type Changes -->
            <div v-if="diff.type_changes" class="space-y-1">
                <h4
                    class="text-xs font-semibold text-muted-foreground uppercase"
                >
                    Type Changes
                </h4>
                <div
                    v-for="(change, path) in diff.type_changes"
                    :key="String(path)"
                    class="rounded border border-border p-2 text-xs"
                >
                    <span class="font-mono text-muted-foreground">{{
                        formatPath(String(path))
                    }}</span>
                    <span class="ml-2"
                        >{{ change.old_type }} &rarr;
                        {{ change.new_type }}</span
                    >
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { X } from 'lucide-vue-next';
import { versionsApi } from '@/api';
import type { VersionSummary } from '@/types/api';

interface Props {
    word: string;
    versions: VersionSummary[];
}

const props = defineProps<Props>();
defineEmits<{ close: [] }>();

const fromVersion = ref(
    props.versions.length > 1
        ? props.versions[1].version
        : props.versions[0]?.version || ''
);
const toVersion = ref(props.versions[0]?.version || '');
const diff = ref<Record<string, any> | null>(null);
const loading = ref(false);

function formatPath(path: string): string {
    // DeepDiff paths look like "root['key']['subkey']" — simplify
    return path
        .replace(/^root/, '')
        .replace(/\['/g, '.')
        .replace(/']/g, '')
        .replace(/^\./, '');
}

function truncateValue(value: any): string {
    const str = typeof value === 'string' ? value : JSON.stringify(value);
    return str.length > 200 ? str.slice(0, 200) + '...' : str;
}

async function loadDiff() {
    if (fromVersion.value === toVersion.value) return;
    loading.value = true;
    diff.value = null;
    try {
        const result = await versionsApi.diff(
            props.word,
            fromVersion.value,
            toVersion.value
        );
        diff.value = result.changes || {};
    } catch {
        diff.value = {};
    } finally {
        loading.value = false;
    }
}
</script>
