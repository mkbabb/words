<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-2xl font-bold">{{ currentWordlist?.name || 'Wordlist' }}</h1>
        <p v-if="currentWordlist?.description" class="text-muted-foreground mt-1">
          {{ currentWordlist.description }}
        </p>
      </div>
    </div>

    <!-- Statistics -->
    <div v-if="currentWordlist" class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div class="bg-muted/30 rounded-lg p-3">
        <div class="text-2xl font-bold">{{ currentWordlist.unique_words }}</div>
        <div class="text-sm text-muted-foreground">Words</div>
      </div>
      <div class="bg-muted/30 rounded-lg p-3">
        <div class="text-2xl font-bold">{{ masteryStats.gold }}</div>
        <div class="text-sm text-muted-foreground">Mastered</div>
      </div>
      <div class="bg-muted/30 rounded-lg p-3">
        <div class="text-2xl font-bold">{{ masteryStats.dueForReview }}</div>
        <div class="text-sm text-muted-foreground">Due</div>
      </div>
      <div class="bg-muted/30 rounded-lg p-3">
        <div class="text-2xl font-bold">{{ progressPercentage }}%</div>
        <div class="text-sm text-muted-foreground">Progress</div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <div v-for="i in 8" :key="i" class="animate-pulse">
        <div class="h-24 bg-muted rounded-lg"></div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!currentWordlist || sortedWords.length === 0" class="text-center py-16">
      <div class="max-w-sm mx-auto">
        <div v-if="!currentWordlist" class="space-y-4">
          <BookOpen class="h-16 w-16 mx-auto text-muted-foreground/50" />
          <h3 class="text-lg font-semibold">No Wordlist Selected</h3>
          <p class="text-muted-foreground">
            Select a wordlist from the sidebar to start learning.
          </p>
        </div>
        <div v-else class="space-y-4">
          <FileText class="h-16 w-16 mx-auto text-muted-foreground/50" />
          <h3 class="text-lg font-semibold">No Words Found</h3>
          <p class="text-muted-foreground">
            Add some words to get started or adjust your filters.
          </p>
        </div>
      </div>
    </div>

    <!-- Word Cards Grid -->
    <div v-else class="space-y-4">
      <div class="grid gap-4 grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
        <WordListCard
          v-for="word in displayWords"
          :key="word.word"
          :word="word"
          @click="handleWordClick"
          @review="handleReview"
          @edit="handleEdit"
        />
      </div>
      
      <!-- Load More Button -->
      <div v-if="hasMoreWords" class="flex justify-center py-6">
        <Button 
          @click="loadMoreWords"
          variant="outline"
          size="lg"
          :disabled="isLoading"
        >
          Load More Words ({{ remainingWords }} remaining)
        </Button>
      </div>
    </div>

    <!-- Modals -->
    <EditWordNotesModal
      v-model="showEditNotesModal"
      :word="editingWord"
      @save="handleUpdateNotes"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { BookOpen, FileText } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import WordListCard from './WordListCard.vue';
import EditWordNotesModal from './EditWordNotesModal.vue';
import type { WordListItem } from '@/types';

// Composables
import { useWordlistStats } from './composables/useWordlistStats';
import { useWordlistFiltering } from './composables/useWordlistFiltering';
import { useWordlistOperations } from './composables/useWordlistOperations';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';

const wordlistMode = useWordlistMode();
const searchBar = useSearchBarStore();
const orchestrator = useSearchOrchestrator({
  query: computed(() => searchBar.searchQuery)
});

// Wordlist operations
const {
  isLoading,
  currentWordlist,
  currentWords,
  loadWordlist,
  loadWords,
  submitReview,
  updateWordNotes,
  clearState
} = useWordlistOperations();

// Stats
const { masteryStats, progressPercentage } = useWordlistStats(currentWords);

// Filtering and sorting
const { sortedWords } = useWordlistFiltering(currentWords);

// Pagination
const PAGE_SIZE = 25;
const currentPage = ref(0);
const displayWords = computed(() => {
  const start = 0;
  const end = (currentPage.value + 1) * PAGE_SIZE;
  return sortedWords.value.slice(start, end);
});

const hasMoreWords = computed(() => {
  return sortedWords.value.length > displayWords.value.length;
});

const remainingWords = computed(() => {
  return Math.max(0, sortedWords.value.length - displayWords.value.length);
});

// Modal state
const showEditNotesModal = ref(false);
const editingWord = ref<WordListItem | null>(null);

// Actions
const handleWordClick = async (word: WordListItem) => {
  searchBar.setMode('lookup');
  searchBar.setQuery(word.word);
  searchBar.setDirectLookup(true);
  try {
    await orchestrator.getDefinition(word.word);
  } finally {
    searchBar.setDirectLookup(false);
  }
};

const handleReview = async (word: WordListItem, quality: number) => {
  if (!currentWordlist.value?.id) return;
  await submitReview(currentWordlist.value.id, word.word, quality);
};

const handleEdit = (word: WordListItem) => {
  editingWord.value = word;
  showEditNotesModal.value = true;
};

const handleUpdateNotes = async (word: WordListItem, notes: string) => {
  if (!currentWordlist.value?.id) return;
  await updateWordNotes(currentWordlist.value.id, word.word, notes);
};

const loadMoreWords = () => {
  currentPage.value++;
};

// Initialize
const initialize = async () => {
  if (wordlistMode.selectedWordlist) {
    await loadWordlist(wordlistMode.selectedWordlist);
    await loadWords(wordlistMode.selectedWordlist);
  }
};

// Watchers
watch(() => wordlistMode.selectedWordlist, async (newId) => {
  if (newId) {
    currentPage.value = 0;
    clearState();
    await initialize();
  } else {
    clearState();
  }
}, { immediate: true });

onMounted(() => {
  initialize();
});
</script>