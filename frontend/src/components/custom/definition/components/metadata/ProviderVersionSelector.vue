<template>
    <div class="space-y-5">
        <!-- Header -->
        <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
                <h3 class="text-sm font-semibold">Re-synthesize from Providers</h3>
                <Badge v-if="currentVersion" variant="secondary" class="font-mono text-micro">
                    v{{ currentVersion }}
                </Badge>
            </div>
            <Button variant="ghost" size="icon" class="h-7 w-7" @click="$emit('close')">
                <X :size="14" />
            </Button>
        </div>

        <p class="text-xs leading-relaxed text-muted-foreground">
            Select which provider versions to include in re-synthesis.
            Each provider entry contributes its definitions to the AI clustering pipeline.
        </p>

        <!-- Loading -->
        <div v-if="loadingProviders" class="space-y-2">
            <div
                v-for="i in 3"
                :key="i"
                class="h-14 animate-pulse rounded-lg bg-muted"
            />
        </div>

        <!-- Provider list -->
        <div v-else-if="providerList.length > 0" class="space-y-2">
            <div
                v-for="(provider, idx) in providerList"
                :key="provider.uniqueKey"
                class="rounded-lg border transition-colors"
                :class="selectedProviders.has(provider.uniqueKey)
                    ? 'border-primary/40 bg-primary/5'
                    : 'border-border bg-background'"
            >
                <div class="flex items-center justify-between gap-3 px-3 py-2.5">
                    <!-- Left: toggle + name -->
                    <button
                        class="flex items-center gap-2.5"
                        @click="toggleProvider(provider.uniqueKey)"
                    >
                        <div
                            class="flex h-4 w-4 items-center justify-center rounded border transition-colors"
                            :class="selectedProviders.has(provider.uniqueKey)
                                ? 'border-primary bg-primary text-primary-foreground'
                                : 'border-muted-foreground/40'"
                        >
                            <Check v-if="selectedProviders.has(provider.uniqueKey)" :size="10" />
                        </div>
                        <span class="text-sm font-medium">{{ provider.displayName }}</span>
                        <Badge
                            v-if="hasDuplicateProvider(provider.name)"
                            variant="outline"
                            class="font-mono text-micro text-muted-foreground"
                        >
                            #{{ idx + 1 }}
                        </Badge>
                    </button>

                    <!-- Right: version selector -->
                    <Select
                        v-if="selectedProviders.has(provider.uniqueKey) && provider.versions.length > 0"
                        :model-value="selectedVersions[provider.uniqueKey] || 'latest'"
                        @update:model-value="selectVersion(provider.uniqueKey, String($event))"
                    >
                        <SelectTrigger class="h-7 w-auto min-w-[7rem] gap-1 px-2 text-xs">
                            <SelectValue placeholder="Latest" />
                        </SelectTrigger>
                        <SelectContent align="end">
                            <SelectItem value="latest">Latest</SelectItem>
                            <SelectItem
                                v-for="v in provider.versions"
                                :key="v.version"
                                :value="v.version"
                            >
                                v{{ v.version }} — {{ formatDate(v.created_at) }}
                            </SelectItem>
                        </SelectContent>
                    </Select>
                    <span
                        v-else-if="selectedProviders.has(provider.uniqueKey)"
                        class="text-micro text-muted-foreground"
                    >
                        No versions
                    </span>
                </div>

                <!-- Definition count hint -->
                <div
                    v-if="selectedProviders.has(provider.uniqueKey) && provider.definitionCount > 0"
                    class="border-t border-border/40 px-3 py-1.5 text-micro text-muted-foreground"
                >
                    {{ provider.definitionCount }} definition{{ provider.definitionCount !== 1 ? 's' : '' }}
                </div>
            </div>
        </div>

        <div v-else class="py-4 text-center text-xs text-muted-foreground">
            No provider data available for this word.
        </div>

        <!-- Options -->
        <div class="flex items-center gap-2">
            <button
                class="flex items-center gap-2"
                @click="autoIncrement = !autoIncrement"
            >
                <div
                    class="flex h-4 w-4 items-center justify-center rounded border transition-colors"
                    :class="autoIncrement
                        ? 'border-primary bg-primary text-primary-foreground'
                        : 'border-muted-foreground/40'"
                >
                    <Check v-if="autoIncrement" :size="10" />
                </div>
                <span class="text-xs text-muted-foreground">Auto-increment version</span>
            </button>
        </div>

        <!-- Actions -->
        <div class="flex justify-end gap-2 border-t border-border/40 pt-3">
            <Button variant="ghost" size="sm" @click="$emit('close')">
                Cancel
            </Button>
            <Button
                size="sm"
                :disabled="synthesizing || selectedProviders.size === 0"
                @click="handleSynthesize"
            >
                <Loader2 v-if="synthesizing" :size="14" class="mr-1.5 animate-spin" />
                {{ synthesizing ? 'Synthesizing...' : 'Re-synthesize' }}
            </Button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { X, Check, Loader2 } from 'lucide-vue-next';
import { Button, Badge, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@mkbabb/glass-ui';
import { versionsApi } from '@/api';
import { providersApi } from '@/api/providers';
import type { VersionSummary, SourceVersionSpec } from '@/types/api';

interface Props {
    word: string;
    currentVersion?: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
    close: [];
    synthesized: [];
}>();

interface ProviderInfo {
    name: string;
    uniqueKey: string;
    displayName: string;
    versions: VersionSummary[];
    definitionCount: number;
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

/** Check if a provider name appears more than once */
function hasDuplicateProvider(name: string): boolean {
    return providerList.value.filter(p => p.name === name).length > 1;
}

function toggleProvider(uniqueKey: string) {
    if (selectedProviders.has(uniqueKey)) {
        selectedProviders.delete(uniqueKey);
    } else {
        selectedProviders.add(uniqueKey);
    }
}

function selectVersion(uniqueKey: string, version: string) {
    selectedVersions[uniqueKey] = version;
}

async function loadProviders() {
    loadingProviders.value = true;
    try {
        const data = await providersApi.getWordProviders(props.word);
        const providers = data.filter((p) => p.provider !== 'synthesis');

        // Track provider name counts for unique key generation
        const nameCount: Record<string, number> = {};

        // Load version history for each provider in parallel
        const results = await Promise.allSettled(
            providers.map(async (p) => {
                nameCount[p.provider] = (nameCount[p.provider] || 0) + 1;
                const idx = nameCount[p.provider];

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
                    uniqueKey: `${p.provider}__${p.id || idx}`,
                    displayName: p.provider
                        .replace(/_/g, ' ')
                        .replace(/\b\w/g, (c) => c.toUpperCase()),
                    versions,
                    definitionCount: p.definitions?.length || 0,
                } satisfies ProviderInfo;
            })
        );

        providerList.value = results
            .filter(
                (r): r is PromiseFulfilledResult<ProviderInfo> =>
                    r.status === 'fulfilled'
            )
            .map((r) => r.value)
            .filter((p) => p.versions.length > 0 || p.definitionCount > 0);

        // Select all providers by default
        for (const p of providerList.value) {
            selectedProviders.add(p.uniqueKey);
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
        for (const uniqueKey of selectedProviders) {
            const provider = providerList.value.find((p) => p.uniqueKey === uniqueKey);
            if (!provider) continue;
            const version = selectedVersions[uniqueKey];
            if (version && version !== 'latest') {
                sources.push({ provider: provider.name, version });
            } else if (provider.versions.length) {
                sources.push({
                    provider: provider.name,
                    version: provider.versions[0].version,
                });
            }
        }

        if (sources.length === 0) {
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
