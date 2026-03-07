<template>
  <div class="space-y-3">
    <!-- Header with toggle between list and diff views -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <h3 class="text-sm font-semibold">Version History</h3>
        <button
          v-if="versions.length >= 2"
          @click="showDiff = !showDiff"
          class="rounded px-1.5 py-0.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          {{ showDiff ? 'List' : 'Compare' }}
        </button>
      </div>
      <button
        @click="$emit('close')"
        class="text-muted-foreground hover:text-foreground rounded p-1 transition-colors"
      >
        <X :size="16" />
      </button>
    </div>

    <!-- Diff Viewer -->
    <VersionDiffViewer
      v-if="showDiff && versions.length >= 2"
      :word="word"
      :versions="versions"
      @close="showDiff = false"
    />

    <!-- Version List -->
    <template v-else>
      <div v-if="loading" class="space-y-2">
        <div v-for="i in 3" :key="i" class="h-12 animate-pulse rounded bg-muted" />
      </div>

      <div v-else-if="versions.length === 0" class="text-muted-foreground py-4 text-center text-sm">
        No version history available.
      </div>

      <div v-else class="max-h-64 space-y-1 overflow-y-auto">
        <div
          v-for="version in versions"
          :key="version.version"
          class="flex items-center justify-between rounded-lg border border-border p-2 text-sm"
        >
          <div>
            <span class="font-mono font-medium">v{{ version.version }}</span>
            <span class="text-muted-foreground ml-2 text-xs">
              {{ formatDate(version.created_at) }}
            </span>
          </div>
          <div class="flex items-center gap-2">
            <button
              v-if="auth.isAdmin && version.version !== currentVersion"
              @click="handlePreview(version.version)"
              class="text-xs text-blue-500 hover:text-blue-600 transition-colors"
            >
              Preview
            </button>
            <button
              v-if="auth.isAdmin && version.version !== currentVersion"
              @click="handleRollback(version.version)"
              class="text-xs text-orange-500 hover:text-orange-600 transition-colors"
              :disabled="rollingBack"
            >
              Rollback
            </button>
            <span
              v-if="version.version === currentVersion"
              class="bg-primary/10 text-primary rounded px-1.5 py-0.5 text-xs font-medium"
            >
              Current
            </span>
          </div>
        </div>
      </div>

      <!-- Preview panel -->
      <div
        v-if="previewContent"
        class="mt-3 rounded border border-border bg-muted/30 p-3"
      >
        <div class="mb-2 flex items-center justify-between">
          <h4 class="text-xs font-semibold text-muted-foreground">
            Preview: v{{ previewVersion }}
          </h4>
          <button
            @click="previewContent = null"
            class="text-xs text-muted-foreground hover:text-foreground"
          >
            Close
          </button>
        </div>
        <pre class="max-h-40 overflow-auto text-xs whitespace-pre-wrap">{{ JSON.stringify(previewContent, null, 2) }}</pre>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { X } from 'lucide-vue-next';
import { useAuthStore } from '@/stores/auth';
import { versionsApi } from '@/api';
import VersionDiffViewer from './VersionDiffViewer.vue';
import type { VersionSummary } from '@/types/api';

interface Props {
  word: string;
  currentVersion?: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{ close: []; rollback: [version: string] }>();

const auth = useAuthStore();
const versions = ref<VersionSummary[]>([]);
const loading = ref(true);
const rollingBack = ref(false);
const showDiff = ref(false);
const previewContent = ref<Record<string, any> | null>(null);
const previewVersion = ref('');

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

async function loadVersions() {
  loading.value = true;
  try {
    const data = await versionsApi.getHistory(props.word);
    versions.value = data.versions || [];
  } catch {
    versions.value = [];
  } finally {
    loading.value = false;
  }
}

async function handlePreview(version: string) {
  try {
    const data = await versionsApi.getVersion(props.word, version);
    previewContent.value = data.content;
    previewVersion.value = version;
  } catch {
    previewContent.value = null;
  }
}

async function handleRollback(version: string) {
  if (!confirm(`Rollback "${props.word}" to version ${version}?`)) return;
  rollingBack.value = true;
  try {
    await versionsApi.rollback(props.word, version);
    emit('rollback', version);
  } catch {
    // Error handling delegated to caller
  } finally {
    rollingBack.value = false;
  }
}

onMounted(loadVersions);
</script>
