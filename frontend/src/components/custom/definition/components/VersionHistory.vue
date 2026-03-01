<template>
  <Transition
    enter-active-class="transition-all duration-350 ease-apple-spring"
    leave-active-class="transition-all duration-200 ease-apple-bounce-in"
    enter-from-class="opacity-0 max-h-0"
    enter-to-class="opacity-100 max-h-[500px]"
    leave-from-class="opacity-100 max-h-[500px]"
    leave-to-class="opacity-0 max-h-0"
  >
    <div
      v-if="show"
      class="overflow-hidden border-t border-border/50 bg-muted/10"
    >
      <div class="px-4 sm:px-6 py-4">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-sm font-semibold">Version History</h3>
          <button
            @click="$emit('close')"
            class="text-muted-foreground hover:text-foreground transition-colors"
          >
            <X :size="14" />
          </button>
        </div>

        <div v-if="loading" class="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 :size="14" class="animate-spin" />
          Loading versions...
        </div>

        <div v-else-if="versions.length === 0" class="text-sm text-muted-foreground">
          No version history available.
        </div>

        <div v-else class="space-y-2 max-h-[300px] overflow-y-auto">
          <div
            v-for="version in versions"
            :key="version.version"
            class="flex items-center justify-between gap-4 rounded-lg border border-border/50 px-3 py-2 text-sm hover:bg-muted/30 transition-colors"
          >
            <div class="flex items-center gap-3 min-w-0">
              <span class="font-mono text-xs text-muted-foreground shrink-0">
                v{{ version.version }}
              </span>
              <span class="text-xs text-muted-foreground truncate">
                {{ formatDate(version.created_at) }}
              </span>
              <span v-if="version.content_hash" class="text-xs text-muted-foreground/50 font-mono truncate max-w-[80px]">
                {{ version.content_hash.slice(0, 8) }}
              </span>
            </div>
            <button
              @click="$emit('rollback', version.version)"
              class="text-xs text-primary hover:underline shrink-0"
            >
              Rollback
            </button>
          </div>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-2 mt-4 pt-3 border-t border-border/30">
          <button
            @click="$emit('create-snapshot')"
            class="text-xs px-3 py-1.5 rounded-md border border-border hover:bg-muted/50 transition-colors"
          >
            Create Snapshot
          </button>
        </div>
      </div>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { X, Loader2 } from 'lucide-vue-next';

interface VersionInfo {
  version: number;
  created_at: string;
  content_hash?: string;
}

interface VersionHistoryProps {
  show: boolean;
  versions: VersionInfo[];
  loading?: boolean;
}

defineProps<VersionHistoryProps>();

defineEmits<{
  close: [];
  rollback: [version: number];
  'create-snapshot': [];
}>();

const formatDate = (dateStr: string) => {
  try {
    const date = new Date(dateStr);
    return date.toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
};
</script>
