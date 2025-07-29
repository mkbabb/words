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
            {{ store.searchQuery ? 'Try adjusting your search or filters.' : 'Add some words to get started.' }}
          </p>
        </div>
      </div>
    </div>

    <!-- Word Cards Grid -->
    <div v-else class="space-y-4">
      <div 
        ref="scrollContainer"
        class="grid gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
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
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import { useAppStore } from '@/stores';
// Removed infinite scroll import
import { 
  BookOpen, 
  FileText, 
  Plus, 
  Upload 
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import type { WordListItem, WordList } from '@/types';
import { MasteryLevel, Temperature } from '@/types/wordlist';
import { wordlistApi } from '@/utils/api';
import WordListCard from './WordListCard.vue';
import WordListUploadModal from './WordListUploadModal.vue';
import CreateWordListModal from './CreateWordListModal.vue';
import EditWordNotesModal from './EditWordNotesModal.vue';

const store = useAppStore();
const router = useRouter();

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
  get: () => store.wordlistSortCriteria,
  set: (value) => { store.wordlistSortCriteria = value; }
});

// Filters - use store filters
const filters = computed(() => store.wordlistFilters);

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
const formatLastAccessed = (lastAccessed: string | null): string => {
  if (!lastAccessed) return 'Never';
  
  const date = new Date(lastAccessed);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));
  
  if (diffMinutes < 1) return 'Just now';
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)}mo ago`;
  
  return `${Math.floor(diffDays / 365)}y ago`;
};

const handleWordClick = async (word: WordListItem) => {
  // Switch to lookup mode for the animation
  store.searchMode = 'lookup';
  
  // Navigate to definition route with smooth transition
  await router.push(`/definition/${encodeURIComponent(word.text)}`);
  
  // Perform the word lookup after navigation
  await store.searchWord(word.text);
};

const handleReview = async (word: WordListItem, quality: number) => {
  try {
    console.log('Processing review:', word.text, 'Quality:', quality);
    
    // Update review data using spaced repetition algorithm
    const response = await wordlistApi.updateWordReview(word.id, {
      quality,
      timestamp: new Date().toISOString()
    });
    
    // Update the word in our local data
    const wordIndex = currentWords.value.findIndex(w => w.id === word.id);
    if (wordIndex >= 0) {
      currentWords.value[wordIndex] = { ...currentWords.value[wordIndex], ...response.data };
    }
    
    console.log('Review completed successfully');
  } catch (error) {
    console.error('Failed to process review:', error);
    // Could show a toast notification here
  }
};

const handleEdit = (word: WordListItem) => {
  console.log('Opening edit dialog for:', word.text);
  editingWord.value = word;
  showEditNotesModal.value = true;
};

const updateWordNotes = async (word: WordListItem, newNotes: string) => {
  try {
    console.log('Updating notes for:', word.text);
    
    const response = await wordlistApi.updateWord(word.id, {
      notes: newNotes
    });
    
    // Update the word in our local data
    const wordIndex = currentWords.value.findIndex(w => w.id === word.id);
    if (wordIndex >= 0) {
      currentWords.value[wordIndex] = { ...currentWords.value[wordIndex], notes: newNotes };
    }
    
    console.log('Notes updated successfully');
  } catch (error) {
    console.error('Failed to update notes:', error);
    alert('Failed to update notes. Please try again.');
  }
};

const handleWordsUploaded = (words: string[]) => {
  console.log('Words uploaded:', words.length);
  // Refresh current wordlist
  // Refresh current wordlist - stub for now
  console.log('Refreshing wordlist data...');
};

const handleWordlistCreated = (wordlist: any) => {
  console.log('Wordlist created:', wordlist.name);
  store.setWordlist(wordlist.id);
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

const loadWordlistWords = async (id: string, page: number = 0, append: boolean = false) => {
  if (!id) return;
  
  if (isLoadingWords.value) {
    return;
  }
  
  isLoadingWords.value = true;
  
  try {
    const response = await wordlistApi.getWordlistWords(id, {
      offset: page * wordsPerPage.value,
      limit: wordsPerPage.value,
      sort: sortCriteria.value || [],
      filters: {},
      search: store.searchQuery || ""
    });
    
    if (append) {
      // Add unique IDs and append
      const newItems = (response.items || []).map((item, idx) => ({
        ...item,
        _uniqueId: `${item.text}-${item.added_date}-${Date.now()}-${idx}`
      }));
      console.log('Appending items:', newItems.length, 'to existing:', currentWords.value.length);
      currentWords.value.splice(currentWords.value.length, 0, ...newItems);
    } else {
      // Add unique IDs for initial load
      const initialItems = (response.items || []).map((item, idx) => ({
        ...item,
        _uniqueId: `${item.text}-${item.added_date}-${Date.now()}-${idx}`
      }));
      console.log('Initial load:', initialItems.length, 'items');
      currentWords.value.splice(0, currentWords.value.length, ...initialItems);
    }
    totalWords.value = response.total || 0;
    currentPage.value = page;
  } catch (error) {
    console.error('Failed to load wordlist words:', error);
  } finally {
    isLoadingWords.value = false;
  }
};

// Clustering is now handled client-side only

const loadMoreWords = async () => {
  if (!store.selectedWordlist || isLoadingWords.value || !hasMoreWords.value) {
    return;
  }
  
  const nextPage = currentPage.value + 1;
  await loadWordlistWords(store.selectedWordlist, nextPage, true);
};

// Infinite scroll removed - using manual Load More button instead

const loadWordlist = async (id: string) => {
  // Reset pagination state
  currentPage.value = 0;
  
  await Promise.all([
    loadWordlistMeta(id),
    loadWordlistWords(id, 0, false)
  ]);
};


// Lifecycle
onMounted(() => {
  if (store.selectedWordlist) {
    loadWordlist(store.selectedWordlist);
  }
});

onUnmounted(() => {
  // Cleanup handled automatically
});

// Watch for wordlist changes  
watch(() => store.selectedWordlist, (newId) => {
  if (newId) {
    loadWordlist(newId);
  } else {
    currentWordlistData.value = null;
    currentWords.value = [];
  }
});


// TEMPORARILY DISABLED - these watchers were causing infinite loops
// watch(() => filters.value, () => {
//   if (store.selectedWordlist) {
//     currentPage.value = 0;
//     loadWordlistWords(store.selectedWordlist, 0, false);
//   }
// }, { deep: true });

// watch(() => sortCriteria.value, () => {
//   if (store.selectedWordlist) {
//     currentPage.value = 0;
//     loadWordlistWords(store.selectedWordlist, 0, false);
//   }
// }, { deep: true });

// Only restart observer when wordlist changes, not on every data append
// Removing this watcher as it causes scroll position issues
</script>

<style scoped>
/* Additional component-specific styles if needed */
</style>