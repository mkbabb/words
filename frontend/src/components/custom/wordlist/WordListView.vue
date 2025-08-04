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
        <div class="text-2xl font-bold">{{ dueForReview }}</div>
        <div class="text-sm text-muted-foreground">Due</div>
      </div>
      <div class="bg-muted/30 rounded-lg p-3">
        <div class="text-2xl font-bold">{{ currentWordlist.learning_stats.streak_days }}</div>
        <div class="text-sm text-muted-foreground">Day Streak</div>
      </div>
    </div>


    <!-- Loading State -->
    <div v-if="isLoading" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <div v-for="i in 8" :key="i" class="animate-pulse">
        <div class="h-24 bg-muted rounded-lg"></div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!currentWordlist || currentWords.length === 0" class="text-center py-16">
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
            {{ searchBar.searchQuery ? 'Try adjusting your search or filters.' : 'Add some words to get started.' }}
          </p>
        </div>
      </div>
    </div>

    <!-- Word Cards Grid -->
    <div v-else class="space-y-4">
      <div 
        ref="scrollContainer"
        class="grid gap-4 grid-cols-2 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
      >
        <WordListCard
          v-for="word in currentWords"
          :key="word._uniqueId"
          :word="word"
          @click="handleWordClick"
          @review="handleReview"
          @edit="handleEdit"
        />
      </div>
      
      <!-- Load More Button -->
      <div v-if="!isLoadingWords && hasMoreWords" class="flex justify-center py-6">
        <Button 
          @click="loadMoreWords"
          variant="outline"
          size="lg"
        >
          Load More Words ({{ remainingWordsCount }} remaining)
        </Button>
      </div>
      
      <!-- Loading indicator -->
      <div v-else-if="isLoadingWords" class="flex items-center justify-center py-4">
        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-primary"></div>
        <span class="text-sm text-muted-foreground ml-2">Loading more...</span>
      </div>
      
      <!-- End of results -->
      <div v-else-if="!hasMoreWords && currentWords.length > 0" class="text-center py-4">
        <span class="text-xs text-muted-foreground">All words loaded</span>
      </div>
    </div>

    <!-- File Upload Modal -->
    <WordListUploadModal 
      v-model="showUploadModal"
      :wordlist-id="currentWordlist?.id"
      @uploaded="handleWordsUploaded"
      @wordlists-updated="() => {}"
    />

    <!-- Create Wordlist Modal -->
    <CreateWordListModal
      v-model="showCreateModal"
      @created="handleWordlistCreated"
    />

    <!-- Edit Word Notes Modal -->
    <EditWordNotesModal
      v-model="showEditNotesModal"
      :word="editingWord"
      @save="updateWordNotes"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
// Removed infinite scroll import
import { 
  BookOpen, 
  FileText
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import type { WordListItem, WordList } from '@/types';
// import { MasteryLevel, Temperature } from '@/types/wordlist';
import { wordlistApi } from '@/api';
import { useToast } from '@/components/ui/toast/use-toast';
// import { formatRelativeTime } from '@/utils';
import WordListCard from './WordListCard.vue';
import WordListUploadModal from './WordListUploadModal.vue';
import CreateWordListModal from './CreateWordListModal.vue';
import EditWordNotesModal from './EditWordNotesModal.vue';

const { searchConfig, orchestrator, loading, searchBar, searchResults } = useStores();
const router = useRouter();
const { toast } = useToast();

// Component state
const isLoadingMeta = ref(false);
const isLoadingWords = ref(false);
const showUploadModal = ref(false);
const showCreateModal = ref(false);
const showEditNotesModal = ref(false);
const editingWord = ref<WordListItem | null>(null);
const currentWordlistData = ref<WordList | null>(null);
const currentWords = ref<any[]>([]);
const totalWords = ref(0);
const currentPage = ref(0);
const wordsPerPage = ref(25);
const scrollContainer = ref<HTMLElement>();

// Sort criteria from store (writeable)
const sortCriteria = computed({
  get: () => searchConfig.wordlistSortCriteria,
  set: (value: any[]) => { searchConfig.setWordlistSortCriteria(value); }
});

// Filters - use store filters
const filters = computed(() => searchConfig.wordlistFilters);

// Computed properties
const currentWordlist = computed(() => currentWordlistData.value);
const isLoading = computed(() => isLoadingMeta.value || isLoadingWords.value);

const hasMoreWords = computed(() => {
  return totalWords.value > currentWords.value.length;
});

const remainingWordsCount = computed(() => {
  return Math.max(0, totalWords.value - currentWords.value.length);
});

const masteryStats = computed(() => {
  if (!currentWords.value || currentWords.value.length === 0) {
    return { bronze: 0, silver: 0, gold: 0 };
  }
  
  return currentWords.value.reduce((acc: Record<string, number>, word: any) => {
    acc[word.mastery_level] = (acc[word.mastery_level] || 0) + 1;
    return acc;
  }, { bronze: 0, silver: 0, gold: 0 });
});

const dueForReview = computed(() => {
  if (!currentWords.value || currentWords.value.length === 0) return 0;
  
  const now = new Date();
  return currentWords.value.filter(word => 
    new Date(word.review_data.next_review_date) <= now
  ).length;
});

// Filtering and sorting are done on backend, using currentWords directly


// Methods

// Convert UI filters to mastery levels array for API
const getMasteryLevelsFromFilters = () => {
  const levels = [];
  if (filters.value.showBronze) levels.push('bronze');
  if (filters.value.showSilver) levels.push('silver');
  if (filters.value.showGold) levels.push('gold');
  // If all are selected or none are selected, return undefined (show all)
  return levels.length === 3 || levels.length === 0 ? undefined : levels;
};

const handleWordClick = async (word: WordListItem) => {
  // Switch to lookup mode and navigate to definition route
  searchConfig.setMode('lookup');
  
  // Perform the word lookup after navigation
  await orchestrator.performSearch(word.word);
};

const handleReview = async (word: WordListItem, quality: number) => {
  try {
    console.log('Processing review:', word.word, 'Quality:', quality);
    
    if (!currentWordlist.value?.id) {
      console.error('No wordlist selected');
      return;
    }
    
    // Submit review to backend
    const response = await wordlistApi.submitWordReview(currentWordlist.value.id, {
      word: word.word,
      quality
    });
    
    // Update the word in our local data with the new review data
    const wordIndex = currentWords.value.findIndex(w => w.word === word.word);
    if (wordIndex >= 0 && response.data) {
      // Update mastery level and last reviewed date based on response
      currentWords.value[wordIndex] = {
        ...currentWords.value[wordIndex],
        mastery_level: response.data.mastery_level || currentWords.value[wordIndex].mastery_level,
        review_data: {
          ...currentWords.value[wordIndex].review_data,
          last_review_date: response.data.last_reviewed || new Date().toISOString()
        }
      };
    }
    
    console.log('Review completed successfully');
  } catch (error) {
    console.error('Failed to process review:', error);
    // Could show a toast notification here
  }
};

const handleEdit = (word: WordListItem) => {
  console.log('Opening edit dialog for:', word.word);
  editingWord.value = word;
  showEditNotesModal.value = true;
};

const updateWordNotes = async (word: WordListItem, newNotes: string) => {
  try {
    console.log('Updating notes for:', word.word);
    
    if (!currentWordlist.value?.id) {
      console.error('No wordlist selected');
      return;
    }
    
    // Note: Backend doesn't have a direct update endpoint yet
    // For now, we'll update locally only
    const wordIndex = currentWords.value.findIndex(w => w.word === word.word);
    if (wordIndex >= 0) {
      currentWords.value[wordIndex] = { ...currentWords.value[wordIndex], notes: newNotes };
    }
    
    console.log('Notes updated locally (backend endpoint pending)');
  } catch (error) {
    console.error('Failed to update notes:', error);
    toast({
      title: "Error",
      description: "Failed to update notes. Please try again.",
      variant: "destructive",
    });
  }
};

const handleWordsUploaded = (words: string[]) => {
  console.log('Words uploaded:', words.length);
  // Refresh current wordlist
  // Refresh current wordlist - stub for now
  console.log('Refreshing wordlist data...');
};

const handleWordlistCreated = async (wordlist: any) => {
  console.log('Wordlist created:', wordlist.name);
  searchConfig.setWordlist(wordlist.id);
  searchConfig.setSearchMode('wordlist', router);
};

// Clustering removed for simplicity

const loadWordlistMeta = async (id: string) => {
  if (!id) return;
  
  console.log('DEBUG: Loading wordlist metadata for ID:', id);
  isLoadingMeta.value = true;
  try {
    const response = await wordlistApi.getWordlist(id);
    console.log('DEBUG: Wordlist metadata response:', response);
    
    currentWordlistData.value = {
      id: response.data._id || response.data.id,
      name: response.data.name,
      description: response.data.description,
      hash_id: response.data.hash_id,
      words: [], // Words loaded separately
      total_words: response.data.total_words,
      unique_words: response.data.unique_words,
      learning_stats: response.data.learning_stats,
      last_accessed: response.data.last_accessed,
      created_at: response.data.created_at,
      updated_at: response.data.updated_at,
      metadata: response.data.metadata || {},
      tags: response.data.tags || [],
      is_public: response.data.is_public || false,
      owner_id: response.data.owner_id,
    };
  } catch (error) {
    console.error('Failed to load wordlist metadata:', error);
  } finally {
    isLoadingMeta.value = false;
  }
};

// Simplified loading - just trigger orchestrator search
const triggerWordlistSearch = () => {
  if (searchConfig.selectedWordlist) {
    // The orchestrator will handle the search based on current query
    orchestrator.executeSearch(searchBar.searchQuery);
  }
};

// Clustering is now handled client-side only

const loadMoreWords = async () => {
  // Pagination will be handled in a future update
  // For now, the orchestrator loads all matching results
  console.log('Load more not yet implemented with new search pipeline');
};

// Infinite scroll removed - using manual Load More button instead


// Watch for filter changes and reload
watch(filters, () => {
  // Reset to first page and reload when filters change
  currentPage.value = 0;
  if (searchConfig.selectedWordlist) {
    triggerWordlistSearch();
  }
}, { deep: true });

// Watch for sort criteria changes and reload
watch(sortCriteria, () => {
  // Reset to first page and reload when sort changes
  currentPage.value = 0;
  if (searchConfig.selectedWordlist) {
    triggerWordlistSearch();
  }
}, { deep: true });

// Lifecycle
onMounted(async () => {
  if (searchConfig.selectedWordlist) {
    await loadWordlistMeta(searchConfig.selectedWordlist);
    triggerWordlistSearch();
  }
});

onUnmounted(() => {
  // Cleanup handled automatically
});

// Watch for wordlist changes  
watch(() => searchConfig.selectedWordlist, async (newId) => {
  if (newId) {
    // Load metadata
    await loadWordlistMeta(newId);
    // Trigger search through orchestrator
    triggerWordlistSearch();
  } else {
    currentWordlistData.value = null;
    currentWords.value = [];
  }
});

// Watch for search results from orchestrator
// The orchestrator now handles all search operations including wordlist searches
watch(() => searchResults.wordlistSearchResults, (results) => {
  if (searchConfig.searchMode === 'wordlist' && results) {
    console.log('📚 WordListView - received search results:', results.length);
    // The orchestrator already updated the dropdown results
    // We just need to update our main display
    if (searchBar.searchQuery.trim()) {
      // Search results - update display
      const newItems = results.map((item: any, idx: number) => ({
        ...item,
        _uniqueId: `${item.word}-${item.added_date || Date.now()}-${idx}`
      }));
      currentWords.value = newItems;
      totalWords.value = results.length;
    }
  }
}, { immediate: true });

// Watch for empty queries to reload all words
watch(() => searchBar.searchQuery, (newQuery) => {
  if (searchConfig.searchMode === 'wordlist' && searchConfig.selectedWordlist && !newQuery.trim()) {
    // Empty query - orchestrator will call getWordlistWords
    // Results will come through wordlistSearchResults watcher
    console.log('📚 WordListView - empty query detected');
  }
});


// TEMPORARILY DISABLED - these watchers were causing infinite loops
// watch(() => filters.value, () => {
//   if (searchConfig.selectedWordlist) {
//     currentPage.value = 0;
//     loadWordlistWords(searchConfig.selectedWordlist, 0, false);
//   }
// }, { deep: true });

// watch(() => sortCriteria.value, () => {
//   if (searchConfig.selectedWordlist) {
//     currentPage.value = 0;
//     loadWordlistWords(searchConfig.selectedWordlist, 0, false);
//   }
// }, { deep: true });

// Only restart observer when wordlist changes, not on every data append
// Removing this watcher as it causes scroll position issues
</script>

<style scoped>
/* Additional component-specific styles if needed */
</style>