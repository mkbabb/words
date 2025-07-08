<template>
  <div
    :class="cn(
      'relative w-full max-w-2xl mx-auto transition-all duration-600 ease-out',
      {
        'transform -translate-y-1/2': moved,
        'transform translate-y-0': !moved,
      },
      className
    )"
  >
    <!-- Logo -->
    <div class="flex items-center justify-center mb-6">
      <h1 
        :class="cn(
          'cursor-pointer select-none flex items-baseline gap-1 transition-all duration-600 ease-out',
          {
            'text-4xl': moved,
            'text-6xl': !moved,
          }
        )"
        @click="resetSearch"
      >
        <LaTeX 
          :expression="'\\mathscr{F}'" 
          :class="cn('text-primary font-bold transition-all duration-600 ease-out', {
            'text-4xl': moved,
            'text-6xl': !moved,
          })"
        />
        <sub :class="cn('font-serif transition-all duration-600 ease-out', {
          'text-xl': moved,
          'text-2xl': !moved,
        })">{{ mode === 'dictionary' ? 'd' : 't' }}</sub>
      </h1>
    </div>

    <!-- Search Input -->
    <div class="relative">
      <Input
        v-model="searchQuery"
        :placeholder="placeholder"
        :class="cn(
          'w-full text-lg px-6 py-4 rounded-full border-2 focus:border-primary transition-all duration-300',
          {
            'text-base py-3': moved,
          }
        )"
        @keydown.enter="handleSearch"
      />
      
      <!-- Search Button -->
      <Button
        :class="cn(
          'absolute right-2 top-1/2 transform -translate-y-1/2 rounded-full px-4 transition-all duration-300',
          {
            'px-3': moved,
          }
        )"
        :disabled="!searchQuery.trim() || isSearching"
        @click="handleSearch"
      >
        <template v-if="isSearching">
          <div class="animate-spin rounded-full h-4 w-4 border-2 border-primary-foreground border-t-transparent"></div>
        </template>
        <template v-else>
          Search
        </template>
      </Button>
    </div>

    <!-- Search Suggestions -->
    <div
      v-if="showSuggestions && suggestions.length > 0"
      class="absolute top-full left-0 right-0 mt-2 bg-popover border border-border rounded-lg shadow-lg z-50 max-h-60 overflow-y-auto"
    >
      <div
        v-for="suggestion in suggestions"
        :key="suggestion"
        class="px-4 py-3 hover:bg-accent cursor-pointer border-b border-border last:border-b-0"
        @click="selectSuggestion(suggestion)"
      >
        {{ suggestion }}
      </div>
    </div>

    <!-- AI Suggestions (only on landing page) -->
    <div
      v-if="!moved && !hasSearched"
      class="mt-8 text-center"
    >
      <p class="text-sm text-muted-foreground mb-4">Try searching for:</p>
      <div class="flex flex-wrap gap-2 justify-center">
        <Button
          v-for="word in aiSuggestions"
          :key="word"
          variant="outline"
          size="sm"
          @click="selectSuggestion(word)"
        >
          {{ word }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { useAppStore } from '@/stores';
import { useSearch } from '@/composables/useSearch';
import { useAnimations } from '@/composables/useAnimations';
import { cn } from '@/utils';
import Button from '@/components/ui/Button.vue';
import Input from '@/components/ui/Input.vue';
import { LaTeX } from '@/components/custom/latex';

interface SearchBarProps {
  className?: string;
}

defineProps<SearchBarProps>();

const store = useAppStore();
const { suggestions, getSuggestions, performSearch } = useSearch();
const { searchBarMoved, transitionToResults } = useAnimations();

const searchQuery = computed({
  get: () => store.searchQuery,
  set: (value) => (store.searchQuery = value),
});

const showSuggestions = ref(false);
const isSearching = computed(() => store.isSearching);
const hasSearched = computed(() => store.hasSearched);
const moved = computed(() => searchBarMoved.value);
const mode = computed(() => store.mode);

const placeholder = computed(() => 
  mode.value === 'dictionary' 
    ? 'Enter a word to define...' 
    : 'Enter a word to find synonyms...'
);

// AI-generated suggestions for landing page
const aiSuggestions = ref([
  'serendipity', 'ephemeral', 'mellifluous', 'petrichor', 
  'wanderlust', 'luminous', 'eloquent', 'ethereal'
]);

// Watch for search query changes to get suggestions
watch(searchQuery, async (newQuery) => {
  if (newQuery.length >= 2) {
    await getSuggestions(newQuery);
    showSuggestions.value = true;
  } else {
    showSuggestions.value = false;
  }
});

// Hide suggestions when clicking outside
onMounted(() => {
  document.addEventListener('click', (e) => {
    const target = e.target as HTMLElement;
    if (!target?.closest('.relative')) {
      showSuggestions.value = false;
    }
  });
});

const handleSearch = async () => {
  if (!searchQuery.value.trim()) return;
  
  showSuggestions.value = false;
  await performSearch(searchQuery.value);
  await transitionToResults();
};

const selectSuggestion = async (suggestion: string) => {
  searchQuery.value = suggestion;
  showSuggestions.value = false;
  await handleSearch();
};

const resetSearch = () => {
  if (moved.value) {
    store.reset();
  }
};
</script>