<template>
    <div class="space-y-4">
        <div class="flex items-center justify-between">
            <h3 class="text-sm font-semibold">Re-synthesize from Versions</h3>
            <button
                @click="$emit('close')"
                class="rounded p-1 text-muted-foreground transition-colors hover:text-foreground"
            >
                <X :size="16" />
            </button>
        </div>

        <p class="text-xs text-muted-foreground">
            Select which provider versions to use for re-synthesis. Defaults to
            latest.
        </p>

        <!-- Loading -->
        <div v-if="loadingProviders" class="space-y-2">
            <div
                v-for="i in 3"
                :key="i"
                class="h-10 animate-pulse rounded bg-muted"
            />
        </div>

        <!-- Provider list with version selectors -->
        <div v-else class="space-y-2">
            <div
                v-for="provider in providerList"
                :key="provider.name"
                class="flex items-center justify-between rounded border border-border p-2"
            >
                <div class="flex items-center gap-2">
                    <input
                        type="checkbox"
                        :checked="selectedProviders.has(provider.name)"
                        @change="toggleProvider(provider.name)"
                        class="rounded border-border"
                    />
                    <span class="text-sm font-medium capitalize">
                        {{ provider.displayName }}
                    </span>
                </div>
                <select
                    v-if="
                        selectedProviders.has(provider.name) &&
                        provider.versions.length > 0
                    "
                    :value="selectedVersions[provider.name] || 'latest'"
                    @change="
                        selectVersion(
                            provider.name,
                            ($event.target as HTMLSelectElement).value
                        )
                    "
                    class="rounded border border-border bg-background px-2 py-1 text-xs"
                >
                    <option value="latest">Latest</option>
                    <option
                        v-for="v in provider.versions"
                        :key="v.version"
                        :value="v.version"
                    >
                        v{{ v.version }} — {{ formatDate(v.created_at) }}
                    </option>
                </select>
                <span
                    v-else-if="selectedProviders.has(provider.name)"
                    class="text-xs text-muted-foreground"
                >
                    No version history
                </span>
            </div>
        </div>

        <!-- Options -->
        <div class="flex items-center gap-3 text-sm">
            <label class="flex items-center gap-1.5">
                <input
                    type="checkbox"
                    v-model="autoIncrement"
                    class="rounded border-border"
                />
                <span class="text-xs text-muted-foreground"
                    >Auto-increment version</span
                >
            </label>
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-2">
            <button
                @click="$emit('close')"
                class="rounded px-3 py-1.5 text-sm hover:bg-muted"
            >
                Cancel
            </button>
            <button
                @click="handleSynthesize"
                :disabled="synthesizing || selectedProviders.size === 0"
                class="rounded bg-primary px-3 py-1.5 text-sm text-primary-foreground transition-colors hover:bg-primary/90 disabled:opacity-50"
            >
                <span v-if="synthesizing">Synthesizing...</span>
                <span v-else>Synthesize from Selected</span>
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { X } from 'lucide-vue-next';
import { versionsApi } from '@/api';
import { providersApi } from '@/api/providers';
import type { VersionSummary, SourceVersionSpec } from '@/types/api';

interface Props {
    word: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
    close: [];
    synthesized: [];
}>();

interface ProviderInfo {
    name: string;
    displayName: string;
    versions: VersionSummary[];
}

const loadingProviders = ref(true);
const synthesizing = ref(false);
const autoIncrement = ref(true);
const providerList = ref<ProviderInfo[]>([]);
const selectedProviders = reactive(new Set<string>());
const selectedVersions = reactive<Record<string, string>>({});

function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
    });
}

function toggleProvider(name: string) {
    if (selectedProviders.has(name)) {
        selectedProviders.delete(name);
    } else {
        selectedProviders.add(name);
    }
}

function selectVersion(provider: string, version: string) {
    selectedVersions[provider] = version;
}

async function loadProviders() {
    loadingProviders.value = true;
    try {
        const data = await providersApi.getWordProviders(props.word);
        const providers = data.filter((p) => p.provider !== 'synthesis');

        // Load version history for each provider in parallel
        const results = await Promise.allSettled(
            providers.map(async (p) => {
                let versions: VersionSummary[] = [];
                try {
                    const history = await versionsApi.getProviderHistory(
                        props.word,
                        p.provider
                    );
                    versions = history.versions || [];
                } catch {
                    // No version history available
                }
                return {
                    name: p.provider,
                    displayName: p.provider
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, (c) => c.toUpperCase()),
                    versions,
                } satisfies ProviderInfo;
            })
        );

        providerList.value = results
            .filter(
                (r): r is PromiseFulfilledResult<ProviderInfo> =>
                    r.status === 'fulfilled'
            )
            .map((r) => r.value);

        // Select all providers by default
        for (const p of providerList.value) {
            selectedProviders.add(p.name);
        }
    } catch {
        providerList.value = [];
    } finally {
        loadingProviders.value = false;
    }
}

async function handleSynthesize() {
    if (selectedProviders.size === 0) return;
    synthesizing.value = true;

    try {
        const sources: SourceVersionSpec[] = [];
        for (const name of selectedProviders) {
            const provider = providerList.value.find((p) => p.name === name);
            const version = selectedVersions[name];
            if (version && version !== 'latest') {
                sources.push({ provider: name, version });
            } else if (provider?.versions.length) {
                // Use latest version
                sources.push({
                    provider: name,
                    version: provider.versions[0].version,
                });
            }
        }

        if (sources.length === 0) {
            // No versioned providers — fall back to regular re-synth
            emit('synthesized');
            return;
        }

        await versionsApi.synthesizeFrom(
            props.word,
            sources,
            autoIncrement.value
        );
        emit('synthesized');
    } catch {
        // Error handling
    } finally {
        synthesizing.value = false;
    }
}

onMounted(loadProviders);
</script>
