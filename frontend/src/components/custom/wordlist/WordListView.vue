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
      
      <!-- Actions -->
      <div class="flex items-center gap-2">
        <Button @click="showUploadModal = true" variant="outline" size="sm">
          <Upload class="h-4 w-4 mr-2" />
          Upload
        </Button>
        <Button @click="showCreateModal = true" variant="default" size="sm">
          <Plus class="h-4 w-4 mr-2" />
          Create
        </Button>
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

    <!-- Search and Filters -->
    <div class="flex items-center gap-4">
      <div class="relative flex-1 max-w-sm">
        <Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          v-model="searchQuery"
          placeholder="Search words..."
          class="pl-10"
          @input="handleSearch"
        />
      </div>
      
      <!-- Mastery filter -->
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button variant="outline" size="sm">
            <Filter class="h-4 w-4 mr-2" />
            Filter
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          <DropdownMenuCheckboxItem
            v-model:checked="filters.showBronze"
            @update:checked="updateFilters"
          >
            <div class="flex items-center">
              <div class="w-3 h-3 rounded-full bg-gradient-to-r from-orange-400 to-orange-600 mr-2"></div>
              Bronze
            </div>
          </DropdownMenuCheckboxItem>
          <DropdownMenuCheckboxItem
            v-model:checked="filters.showSilver"
            @update:checked="updateFilters"
          >
            <div class="flex items-center">
              <div class="w-3 h-3 rounded-full bg-gradient-to-r from-gray-400 to-gray-600 mr-2"></div>
              Silver
            </div>
          </DropdownMenuCheckboxItem>
          <DropdownMenuCheckboxItem
            v-model:checked="filters.showGold"
            @update:checked="updateFilters"
          >
            <div class="flex items-center">
              <div class="w-3 h-3 rounded-full bg-gradient-to-r from-yellow-400 to-amber-600 mr-2"></div>
              Gold
            </div>
          </DropdownMenuCheckboxItem>
          <DropdownMenuSeparator />
          <DropdownMenuCheckboxItem
            v-model:checked="filters.showHotOnly"
            @update:checked="updateFilters"
          >
            🔥 Recently Studied
          </DropdownMenuCheckboxItem>
          <DropdownMenuCheckboxItem
            v-model:checked="filters.showDueOnly"
            @update:checked="updateFilters"
          >
            ⏰ Due for Review
          </DropdownMenuCheckboxItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>

    <!-- Loading State -->
    <div v-if="isLoading" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <div v-for="i in 8" :key="i" class="animate-pulse">
        <div class="h-24 bg-muted rounded-lg"></div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else-if="!currentWordlist || filteredWords.length === 0" class="text-center py-16">
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
            {{ searchQuery ? 'Try adjusting your search or filters.' : 'Add some words to get started.' }}
          </p>
        </div>
      </div>
    </div>

    <!-- Word Cards Grid -->
    <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <WordListCard
        v-for="word in filteredWords"
        :key="word.text"
        :word="word"
        @click="handleWordClick"
        @review="handleReview"
        @edit="handleEdit"
      />
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useAppStore } from '@/stores';
import { 
  BookOpen, 
  FileText, 
  Plus, 
  Upload, 
  Search, 
  Filter 
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuTrigger,
  DropdownMenuCheckboxItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import type { WordListItem, MasteryLevel, Temperature } from '@/types';
import WordListCard from './WordListCard.vue';
import WordListUploadModal from './WordListUploadModal.vue';
import CreateWordListModal from './CreateWordListModal.vue';

const store = useAppStore();

// Component state
const searchQuery = ref('');
const isLoading = ref(false);
const showUploadModal = ref(false);
const showCreateModal = ref(false);

// Filters
const filters = ref({
  showBronze: true,
  showSilver: true,
  showGold: true,
  showHotOnly: false,
  showDueOnly: false,
});

// Computed properties
const currentWordlist = computed(() => store.currentWordlist);

const masteryStats = computed(() => {
  if (!currentWordlist.value?.words) {
    return { bronze: 0, silver: 0, gold: 0 };
  }
  
  return currentWordlist.value.words.reduce((acc, word) => {
    acc[word.mastery_level]++;
    return acc;
  }, { bronze: 0, silver: 0, gold: 0 } as Record<MasteryLevel, number>);
});

const dueForReview = computed(() => {
  if (!currentWordlist.value?.words) return 0;
  
  const now = new Date();
  return currentWordlist.value.words.filter(word => 
    new Date(word.review_data.next_review_date) <= now
  ).length;
});

const filteredWords = computed(() => {
  if (!currentWordlist.value?.words) return [];
  
  let words = currentWordlist.value.words;
  
  // Apply search filter
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase();
    words = words.filter(word => 
      word.text.toLowerCase().includes(query) ||
      word.notes.toLowerCase().includes(query) ||
      word.tags.some(tag => tag.toLowerCase().includes(query))
    );
  }
  
  // Apply mastery filters
  words = words.filter(word => {
    const showMastery = 
      (filters.value.showBronze && word.mastery_level === 'bronze') ||
      (filters.value.showSilver && word.mastery_level === 'silver') ||
      (filters.value.showGold && word.mastery_level === 'gold');
    
    if (!showMastery) return false;
    
    // Apply additional filters
    if (filters.value.showHotOnly && word.temperature !== 'hot') return false;
    if (filters.value.showDueOnly) {
      const now = new Date();
      const dueDate = new Date(word.review_data.next_review_date);
      if (dueDate > now) return false;
    }
    
    return true;
  });
  
  // Sort by mastery, then by frequency, then by last visited
  return words.sort((a, b) => {
    // First sort by mastery level (gold > silver > bronze)
    const masteryOrder = { gold: 3, silver: 2, bronze: 1 };
    const masteryDiff = masteryOrder[b.mastery_level] - masteryOrder[a.mastery_level];
    if (masteryDiff !== 0) return masteryDiff;
    
    // Then by frequency (higher frequency first)
    const freqDiff = b.frequency - a.frequency;
    if (freqDiff !== 0) return freqDiff;
    
    // Finally by last visited (more recent first)
    const aDate = a.last_visited ? new Date(a.last_visited) : new Date(0);
    const bDate = b.last_visited ? new Date(b.last_visited) : new Date(0);
    return bDate.getTime() - aDate.getTime();
  });
});

// Methods
const handleSearch = async () => {
  // Debounce search to avoid excessive API calls
  if (searchQuery.value.trim() && currentWordlist.value) {
    // Could implement corpus search here for real-time filtering
    console.log('Searching:', searchQuery.value);
  }
};

const updateFilters = () => {
  // Filters are reactive, no additional action needed
};

const handleWordClick = (word: WordListItem) => {
  // Navigate to word definition or open details modal
  console.log('Word clicked:', word.text);
  // store.searchWord(word.text);
};

const handleReview = (word: WordListItem, quality: number) => {
  // Handle spaced repetition review
  console.log('Review:', word.text, 'Quality:', quality);
  // Call API to record review
};

const handleEdit = (word: WordListItem) => {
  // Open edit modal for word
  console.log('Edit word:', word.text);
};

const handleWordsUploaded = (words: string[]) => {
  console.log('Words uploaded:', words.length);
  // Refresh current wordlist
  if (currentWordlist.value) {
    store.fetchWordlist(currentWordlist.value.id);
  }
};

const handleWordlistCreated = (wordlist: any) => {
  console.log('Wordlist created:', wordlist.name);
  store.selectWordlist(wordlist);
};

// Lifecycle
onMounted(() => {
  // Load initial data if needed
  if (!currentWordlist.value && store.selectedWordlist) {
    store.fetchWordlist(store.selectedWordlist);
  }
});

// Watch for wordlist changes
watch(() => store.selectedWordlist, (newId) => {
  if (newId) {
    isLoading.value = true;
    store.fetchWordlist(newId).finally(() => {
      isLoading.value = false;
    });
  }
});
</script>

<style scoped>
/* Additional component-specific styles if needed */
</style>