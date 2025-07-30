<template>
  <button
    @click="$emit('select', wordlist)"
    :class="[
      'group flex w-full items-center justify-between rounded-md px-3 py-2',
      'transition-all duration-200',
      'text-left',
      isSelected 
        ? 'bg-primary/10 text-primary border border-primary/20' 
        : 'hover:bg-muted/50 active:scale-[0.98]',
      'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-1'
    ]"
  >
    <div class="min-w-0 flex-1">
      <div class="flex items-center gap-2">
        <p class="font-medium text-sm truncate">{{ wordlist.name }}</p>
        
        <!-- Mastery indicator dots -->
        <div class="flex items-center gap-0.5">
          <div 
            v-if="masteryStats.gold > 0"
            class="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-yellow-400 to-amber-600"
            :title="`${masteryStats.gold} mastered`"
          />
          <div 
            v-if="masteryStats.silver > 0"
            class="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-gray-400 to-gray-600"
            :title="`${masteryStats.silver} familiar`"
          />
          <div 
            v-if="masteryStats.bronze > 0"
            class="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-orange-400 to-orange-600"
            :title="`${masteryStats.bronze} learning`"
          />
        </div>
      </div>
      
      <div class="flex items-center gap-2 mt-0.5">
        <p class="text-xs text-muted-foreground">
          {{ wordlist.unique_words }} words
        </p>
        <span class="text-xs text-muted-foreground">•</span>
        <p class="text-xs text-muted-foreground">
          {{ formatLastAccessed(wordlist.last_accessed) }}
        </p>
      </div>
      
      <!-- Progress bar -->
      <div v-if="!isPublic" class="mt-1 w-full">
        <div class="h-1 w-full bg-muted rounded-full overflow-hidden">
          <div 
            class="h-full bg-gradient-to-r from-primary/60 to-primary transition-all duration-300"
            :style="{ width: `${masteryProgress}%` }"
          />
        </div>
      </div>
    </div>
    
    <!-- Action menu -->
    <div class="ml-2 opacity-60 hover:opacity-100 transition-opacity duration-200">
      <DropdownMenu>
        <DropdownMenuTrigger as-child @click.stop>
          <Button variant="ghost" size="sm" class="h-6 w-6 p-0">
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
</template>

<script setup lang="ts">
import { computed } from 'vue';
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
import type { WordList, MasteryLevel } from '@/types';

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

// Computed properties
const masteryStats = computed(() => {
  if (!props.wordlist.words || props.wordlist.words.length === 0) {
    return { bronze: 0, silver: 0, gold: 0 };
  }
  
  return props.wordlist.words.reduce((acc, word) => {
    acc[word.mastery_level]++;
    return acc;
  }, { bronze: 0, silver: 0, gold: 0 } as Record<MasteryLevel, number>);
});

const masteryProgress = computed(() => {
  const total = props.wordlist.unique_words;
  if (total === 0) return 0;
  
  const mastered = masteryStats.value.gold;
  const familiar = masteryStats.value.silver;
  
  // Weight gold more heavily than silver
  const progress = ((mastered * 1.0) + (familiar * 0.6)) / total;
  return Math.min(Math.round(progress * 100), 100);
});

// Methods
const formatLastAccessed = (lastAccessed: string | null): string => {
  if (!lastAccessed) return 'Never';
  
  const date = new Date(lastAccessed);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  
  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
  
  return `${Math.floor(diffDays / 365)}y ago`;
};

const confirmDelete = () => {
  if (confirm(`Are you sure you want to delete "${props.wordlist.name}"?`)) {
    emit('delete', props.wordlist);
  }
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