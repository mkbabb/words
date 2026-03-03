<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold">Version History</h3>
      <button
        @click="$emit('close')"
        class="text-muted-foreground hover:text-foreground rounded p-1 transition-colors"
      >
        <X :size="16" />
      </button>
    </div>

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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { X } from 'lucide-vue-next';
import { useAuthStore } from '@/stores/auth';
import { versionsApi } from '@/api';

interface Props {
  word: string;
  currentVersion?: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{ close: []; rollback: [version: string] }>();

const auth = useAuthStore();
const versions = ref<Array<{ version: string; created_at: string; content_hash?: string }>>([]);
const loading = ref(true);
const rollingBack = ref(false);

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
