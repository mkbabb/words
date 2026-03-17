<template>
  <button
    @click="$emit('select', wordlist)"
    :title="wordlist.name"
    :class="[
      'group flex w-full items-center justify-between rounded-lg px-2 py-1.5',
      'transition-all duration-200',
      'text-left',
      isSelected
        ? 'bg-primary/10 text-foreground'
        : 'text-foreground/80 hover:bg-muted/30 hover:text-foreground',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1'
    ]"
  >
    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-1.5">
        <p :class="[
          'truncate text-sm',
          isSelected ? 'font-bold' : 'font-medium'
        ]">{{ wordlist.name }}</p>

        <!-- Mastery indicator dot -->
        <div
          v-if="hasMastered"
          class="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-gradient-to-r from-yellow-400 to-amber-600"
          :title="`${props.wordlist.learning_stats?.words_mastered ?? 0} mastered`"
        />
        <!-- Active indicator (matches SidebarCluster) -->
        <div
          v-if="isSelected"
          class="ml-auto h-2 w-2 flex-shrink-0 rounded-full bg-primary/30 transition-all duration-300"
        />
      </div>

      <div class="flex items-center gap-1.5 mt-0.5">
        <span class="text-micro text-muted-foreground/70 tabular-nums">
          {{ wordlist.unique_words }} words
        </span>
        <span class="text-micro text-muted-foreground/50">·</span>
        <span class="text-micro text-muted-foreground/70">
          {{ formatRelativeTime(wordlist.last_accessed) }}
        </span>
      </div>

      <!-- Progress bar -->
      <div v-if="!isPublic && masteryProgress > 0" class="mt-1 w-full">
        <div class="h-0.5 w-full rounded-full bg-muted/50 overflow-hidden">
          <div
            :class="[
                'h-full transition-all duration-300 rounded-full',
                masteryProgress >= 80
                    ? 'bg-gradient-to-r from-yellow-400/60 to-amber-500/70'
                    : masteryProgress >= 40
                        ? 'bg-gradient-to-r from-gray-300/60 to-gray-400/70'
                        : 'bg-gradient-to-r from-primary/40 to-primary/70'
            ]"
            :style="{ width: `${masteryProgress}%` }"
          />
        </div>
      </div>
    </div>

    <!-- Action menu (only visible on hover) -->
    <div class="ml-1 opacity-0 group-hover:opacity-60 hover:!opacity-100 transition-opacity duration-200">
      <DropdownMenu>
        <DropdownMenuTrigger as-child @click.stop>
          <Button variant="ghost" size="sm" class="h-5 w-5 p-0">
            <MoreVertical class="h-3 w-3" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem v-if="!isPublic" @click.stop="$emit('edit', wordlist)">
            <Edit2 class="h-3 w-3 mr-2" />
            Edit
          </DropdownMenuItem>

          <DropdownMenuItem @click.stop="$emit('duplicate', wordlist)">
            <Copy class="h-3 w-3 mr-2" />
            Duplicate
          </DropdownMenuItem>

          <DropdownMenuSeparator />

          <DropdownMenuItem @click.stop="handleExport" class="text-muted-foreground">
            <Download class="h-3 w-3 mr-2" />
            Export
          </DropdownMenuItem>

          <DropdownMenuItem v-if="!isPublic" @click.stop="confirmDelete" class="text-destructive">
            <Trash2 class="h-3 w-3 mr-2" />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  </button>

  <ConfirmDialog
    v-model:open="showDeleteDialog"
    title="Delete Wordlist"
    :description="`Are you sure you want to delete &quot;${wordlist.name}&quot;?`"
    message="This action cannot be undone. All words and progress will be permanently deleted."
    confirm-text="Delete"
    cancel-text="Cancel"
    :destructive="true"
    @confirm="handleConfirmDelete"
  />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import { 
  Copy,
  Download,
  Edit2,
  MoreVertical,
  Trash2,
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import ConfirmDialog from '../ConfirmDialog.vue';
import type { WordList } from '@/types';
import { formatRelativeTime } from '@/utils';

interface Props {
  wordlist: WordList;
  isSelected?: boolean;
  isPublic?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  isSelected: false,
  isPublic: false,
});

const emit = defineEmits<{
  select: [wordlist: WordList];
  edit: [wordlist: WordList];
  delete: [wordlist: WordList];
  duplicate: [wordlist: WordList];
}>();

// Dialog state
const showDeleteDialog = ref(false);

// Derived from learning_stats metadata (always populated) instead of empty words[]
const hasMastered = computed(() => (props.wordlist.learning_stats?.words_mastered ?? 0) > 0);

const masteryProgress = computed(() => {
  const total = props.wordlist.unique_words ?? 0;
  if (!total) return 0;
  const mastered = props.wordlist.learning_stats?.words_mastered ?? 0;
  return Math.min(Math.round((mastered / total) * 100), 100);
});

// Methods

const confirmDelete = () => {
  showDeleteDialog.value = true;
};

const handleConfirmDelete = () => {
  emit('delete', props.wordlist);
  showDeleteDialog.value = false;
};

const handleExport = () => {
  // Create a simple CSV export
  const words = props.wordlist.words || [];
  const csvContent = [
    'word,mastery_level,frequency,last_visited,notes',
    ...words.map(word => [
      word.word,
      word.mastery_level,
      word.frequency,
      word.last_visited || '',
      word.notes.replace(/,/g, ';') // Replace commas to avoid CSV issues
    ].join(','))
  ].join('\n');
  
  const blob = new Blob([csvContent], { type: 'text/csv' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${props.wordlist.name.replace(/[^a-zA-Z0-9]/g, '_')}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};
</script>

<style scoped>
/* Custom styles for wordlist items */
</style>