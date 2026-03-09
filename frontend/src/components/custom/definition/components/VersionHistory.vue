<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <h3 class="text-sm font-semibold">Version History</h3>
        <Badge v-if="currentVersion" variant="secondary" class="font-mono text-[10px]">
          v{{ currentVersion }}
        </Badge>
        <Button
          v-if="versions.length >= 2"
          variant="ghost"
          size="sm"
          class="h-6 px-2 text-xs"
          @click="showDiff = !showDiff"
        >
          {{ showDiff ? 'List' : 'Compare' }}
        </Button>
      </div>
      <Button variant="ghost" size="icon" class="h-7 w-7" @click="$emit('close')">
        <X :size="14" />
      </Button>
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
        <div v-for="i in 3" :key="i" class="h-14 animate-pulse rounded-lg bg-muted" />
      </div>

      <div v-else-if="versions.length === 0" class="py-6 text-center text-sm text-muted-foreground">
        No version history available.
      </div>

      <div v-else class="max-h-72 space-y-1.5 overflow-y-auto">
        <div
          v-for="version in versions"
          :key="version.version"
          class="rounded-lg border border-border p-3 transition-colors"
          :class="version.version === currentVersion ? 'bg-primary/5 border-primary/30' : 'bg-background'"
        >
          <div class="flex items-center justify-between">
            <!-- Version info -->
            <div class="flex items-center gap-2">
              <Badge
                :variant="version.version === currentVersion ? 'default' : 'outline'"
                class="font-mono text-[10px]"
              >
                v{{ version.version }}
              </Badge>
              <span class="text-xs text-muted-foreground">
                {{ formatDate(version.created_at) }}
              </span>
              <Badge
                v-if="version.is_latest"
                variant="secondary"
                class="text-[10px]"
              >
                Latest
              </Badge>
            </div>

            <!-- Actions -->
            <div class="flex items-center gap-1.5">
              <Button
                v-if="auth.isAdmin && version.version !== currentVersion"
                variant="ghost"
                size="sm"
                class="h-6 px-2 text-xs text-blue-500 hover:text-blue-600"
                @click="handlePreview(version.version)"
              >
                <Eye :size="12" class="mr-1" />
                Preview
              </Button>
              <Button
                v-if="auth.isAdmin && version.version !== currentVersion"
                variant="ghost"
                size="sm"
                class="h-6 px-2 text-xs text-orange-500 hover:text-orange-600"
                :disabled="rollingBack"
                @click="handleRollback(version.version)"
              >
                <RotateCcw :size="12" class="mr-1" />
                Rollback
              </Button>
              <Badge
                v-if="version.version === currentVersion"
                class="text-[10px]"
              >
                Current
              </Badge>
            </div>
          </div>

          <!-- Storage mode indicator -->
          <div class="mt-1 text-[10px] text-muted-foreground/60">
            {{ version.storage_mode === 'snapshot' ? 'Full snapshot' : 'Delta' }}
          </div>
        </div>
      </div>

      <!-- Preview panel -->
      <div
        v-if="previewContent"
        class="mt-3 space-y-2.5 rounded-lg border border-primary/20 bg-primary/5 p-3"
      >
        <div class="flex items-center justify-between">
          <div class="flex items-center gap-2">
            <h4 class="text-xs font-semibold">Preview</h4>
            <Badge variant="outline" class="font-mono text-[10px]">v{{ previewVersion }}</Badge>
          </div>
          <Button variant="ghost" size="sm" class="h-6 px-2 text-xs" @click="previewContent = null">
            Close
          </Button>
        </div>

        <!-- Definitions summary -->
        <div v-if="previewContent.definition_ids" class="flex items-center gap-1.5 text-xs">
          <span class="text-muted-foreground">Definitions:</span>
          <span class="font-medium">{{ previewContent.definition_ids.length }}</span>
        </div>

        <!-- Source entries -->
        <div v-if="previewContent.source_entries?.length" class="flex flex-wrap items-center gap-1.5 text-xs">
          <span class="text-muted-foreground">Sources:</span>
          <Badge
            v-for="(src, i) in previewContent.source_entries"
            :key="i"
            variant="secondary"
            class="text-[10px] capitalize"
          >
            {{ src.provider }} ({{ src.entry_version }})
          </Badge>
        </div>

        <!-- Etymology snippet -->
        <div v-if="previewContent.etymology?.text" class="text-xs">
          <span class="text-muted-foreground">Etymology:</span>
          <p class="mt-0.5 line-clamp-2 italic text-foreground/70">
            {{ previewContent.etymology.text }}
          </p>
        </div>

        <!-- Model info -->
        <div v-if="previewContent.model_info" class="flex items-center gap-3 text-xs text-muted-foreground">
          <span>Model: <span class="font-mono font-medium text-foreground/80">{{ previewContent.model_info.name }}</span></span>
          <span>Tokens: <span class="font-medium text-foreground/80">{{ previewContent.model_info.total_tokens?.toLocaleString() }}</span></span>
        </div>

        <!-- Created/updated -->
        <div v-if="previewContent.created_at" class="text-[10px] text-muted-foreground">
          Created {{ formatDate(previewContent.created_at) }}
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { X, Eye, RotateCcw } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
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
