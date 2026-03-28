<template>
  <Tabs
    :model-value="modelValue"
    @update:model-value="$emit('update:modelValue', $event as string)"
    class="w-full"
  >
    <!-- No TabsList — source switching is controlled by ProviderIcons in WordHeader -->

    <!-- AI Synthesis content (default slot) -->
    <TabsContent v-if="showSynthesis" value="synthesis" class="mt-0 tab-content-animate">
      <slot />
    </TabsContent>

    <!-- Provider data tabs (pre-created for each available provider) -->
    <TabsContent
      v-for="providerName in availableProviders"
      :key="providerName"
      :value="providerName"
      class="mt-0 tab-content-animate"
    >
      <div class="px-4 pb-4 sm:px-6">
        <!-- Per-provider version history (admin mode) -->
        <div
          v-if="showVersionHistory && providerVersions[providerName]?.length"
          class="mb-3 flex items-center gap-2 text-xs text-muted-foreground"
        >
          <span class="font-medium">Version:</span>
          <select
            class="rounded border border-border bg-background px-1.5 py-0.5 text-xs"
            :value="'latest'"
            @change="handleProviderVersionChange(providerName, ($event.target as HTMLSelectElement).value)"
          >
            <option value="latest">Latest</option>
            <option
              v-for="v in providerVersions[providerName]"
              :key="v.version"
              :value="v.version"
            >
              v{{ v.version }} — {{ formatVersionDate(v.created_at) }}
            </option>
          </select>
        </div>

        <ProviderDataView
          v-if="getLoadedProvider(providerName)"
          :provider="getLoadedProvider(providerName)!"
          :edit-mode-enabled="editModeEnabled"
        />
        <!-- Loading skeleton while provider data is being fetched -->
        <div v-else class="animate-pulse space-y-3 py-4">
          <div class="h-4 w-24 rounded bg-muted" />
          <div class="h-4 w-full rounded bg-muted" />
          <div class="h-4 w-3/4 rounded bg-muted" />
          <div class="h-4 w-1/2 rounded bg-muted" />
        </div>
      </div>
    </TabsContent>
  </Tabs>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue';
import { Tabs, TabsContent } from '@mkbabb/glass-ui';
import ProviderDataView from './ProviderDataView.vue';
import { providersApi, type ProviderEntry } from '@/api/providers';
import { versionsApi } from '@/api';
import type { VersionSummary } from '@/types/api';

interface Props {
  modelValue: string;
  word: string;
  availableProviders?: string[];
  showSynthesis?: boolean;
  showVersionHistory?: boolean;
  editModeEnabled?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  availableProviders: () => [],
  showSynthesis: true,
  showVersionHistory: false,
  editModeEnabled: false,
});

const emit = defineEmits<{
  'update:modelValue': [value: string];
}>();

const providers = ref<ProviderEntry[]>([]);
const loaded = ref(false);
const providerVersions = reactive<Record<string, VersionSummary[]>>({});

function formatVersionDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

async function loadProviderVersions(providerName: string) {
  if (providerVersions[providerName]) return;
  try {
    const data = await versionsApi.getProviderHistory(props.word, providerName);
    providerVersions[providerName] = data.versions || [];
  } catch {
    providerVersions[providerName] = [];
  }
}

function handleProviderVersionChange(_providerName: string, _version: string) {
  // Future: load specific version content
}

function getLoadedProvider(name: string): ProviderEntry | undefined {
  return providers.value.find((p) => p.provider === name);
}

async function loadProviders() {
  if (!props.word || loaded.value) return;
  try {
    const data = await providersApi.getWordProviders(props.word);
    providers.value = data.filter((p) => p.provider !== 'synthesis');
    loaded.value = true;
  } catch {
    // Provider data is optional — silent failure
  }
}

// Reset provider cache when word changes
watch(() => props.word, () => {
  loaded.value = false;
  providers.value = [];
  Object.keys(providerVersions).forEach(k => delete providerVersions[k]);
  if (props.showSynthesis) {
    emit('update:modelValue', 'synthesis');
    return;
  }
  if (props.availableProviders.length > 0) {
    emit('update:modelValue', props.availableProviders[0]);
  }
});

// Validate active tab & load provider data when tab/providers/showSynthesis change.
// Consolidates tab-validation and data-loading into a single watcher.
watch(
  () => [props.availableProviders, props.showSynthesis, props.modelValue] as const,
  ([availableProviders, showSynthesis, activeTab]) => {
    // 1. Ensure current tab is still valid
    const validTabs = showSynthesis
      ? ['synthesis', ...availableProviders]
      : [...availableProviders];

    if (validTabs.length > 0 && !validTabs.includes(activeTab)) {
      emit('update:modelValue', validTabs[0]);
      return; // Will re-fire with corrected tab
    }

    // 2. Load provider data when on a non-synthesis tab
    if (activeTab !== 'synthesis') {
      if (!loaded.value) {
        loadProviders();
      }
      if (props.showVersionHistory) {
        loadProviderVersions(activeTab);
      }
    }
  },
  { immediate: true },
);

// Pre-load on mount
onMounted(loadProviders);
</script>

<style scoped>
/* Tab content entrance animation — Reka UI mounts/unmounts TabsContent,
   so a CSS animation on mount gives us the fade+slide without Vue <Transition>. */
@keyframes tab-content-in {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
}
.tab-content-animate {
    animation: tab-content-in 0.25s ease both;
}
</style>
