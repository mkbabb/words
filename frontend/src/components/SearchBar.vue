<template>
  <div
    :class="cn(
      'relative w-full transition-all duration-600 ease-out',
      {
        'transform -translate-y-1/2': moved,
        'transform translate-y-0': !moved,
      },
      className
    )"
  >
    <!-- Search Container with Card Shadow -->
    <div class="max-w-lg mx-auto card-shadow rounded-2xl bg-background p-4">
      <!-- Logo and Search Bar Container -->
      <div class="flex items-center justify-center gap-2 mb-4">
        <!-- Dictionary/Thesaurus Toggle Logo -->
        <div 
          :class="cn(
            'bg-gradient-to-br from-primary/10 to-primary/5 rounded-lg cursor-pointer transition-all duration-300 ease-out hover:scale-110 active:scale-95 flex items-center justify-center',
            {
              'w-10 h-10': moved,
              'w-12 h-12': !moved,
            }
          )"
          @click="store.toggleMode()"
          :title="`Switch to ${mode === 'dictionary' ? 'Thesaurus' : 'Dictionary'} mode`"
        >
          <LaTeX 
            :expression="`\\mathfrak{F}_{\\text{${mode === 'dictionary' ? 'd' : 't'}}}`"
            :class="cn('text-primary font-bold transition-all duration-300 ease-out', {
              'text-sm': moved,
              'text-lg': !moved,
            })"
          />
        </div>

        <!-- Search Input Container -->
        <div class="relative flex-1">
          <!-- Search Icon Overlay -->
          <div class="absolute left-3 top-1/2 transform -translate-y-1/2 z-10">
            <Search 
              :size="moved ? 14 : 16" 
              class="text-muted-foreground"
            />
          </div>
          
          <Input
            v-model="searchQuery"
            :placeholder="placeholder"
            :class="cn(
              'w-full pl-10 pr-4 rounded-xl border-0 focus:border-primary transition-all duration-300 bg-muted/30 focus:bg-background',
              {
                'py-2 text-sm': moved,
                'py-3 text-base': !moved,
              }
            )"
            @keydown.enter="handleSearch"
          />
          
          <!-- Progress Bar -->
          <div 
            v-if="isSearching"
            class="absolute bottom-0 left-0 h-1 bg-primary/20 rounded-b-xl overflow-hidden w-full"
          >
            <div class="h-full bg-primary rounded-b-xl animate-pulse"></div>
          </div>
        </div>
      </div>

      <!-- Search Suggestions -->
      <div
        v-if="showSuggestions && suggestions.length > 0"
        class="mt-2 bg-background rounded-xl max-h-60 overflow-y-auto"
      >
        <div
          v-for="(suggestion, index) in suggestions.slice(0, 4)"
          :key="suggestion"
          :class="cn(
            'px-3 py-2 cursor-pointer border-b border-border/30 last:border-b-0 transition-all duration-200 hover:bg-muted/50 hover:scale-[1.01]',
            {
              'bg-muted/30': index === 0,
            }
          )"
          @click="selectSuggestion(suggestion)"
        >
          <span class="text-xs text-muted-foreground/60">{{ suggestion }}</span>
        </div>
      </div>
      
      <!-- Progressive Loading Bar -->
      <div 
        v-if="isSearching"
        class="mt-3 w-full"
      >
        <div class="h-1 bg-muted/20 rounded-full overflow-hidden">
          <div class="h-full bg-gradient-to-r from-purple-300 via-purple-400 to-purple-500 rounded-full transition-all duration-300 ease-out animate-pulse" 
               :style="{ width: `${loadingProgress}%` }"></div>
        </div>
        <div v-if="store.loadingStage" class="text-xs text-muted-foreground mt-1 text-center">
          {{ store.loadingStage }}
        </div>
      </div>
    </div>

    <!-- AI Suggestions (only on landing page) -->
    <div
      v-if="!moved && !hasSearched"
      class="mt-6 max-w-lg mx-auto"
    >
      <div class="p-4 rounded-2xl bg-muted/5 card-shadow">
        <div class="flex flex-wrap gap-2 justify-center">
          <Button
            v-for="word in aiSuggestions.slice(0, 4)"
            :key="word"
            variant="outline"
            size="sm"
            class="rounded-xl hover:scale-110 transition-all duration-300 text-xs active:scale-95"
            @click="selectSuggestion(word)"
          >
            {{ word }}
          </Button>
        </div>
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
// import Badge from '@/components/ui/Badge.vue';
import { LaTeX } from '@/components/custom/latex';
import { Search } from 'lucide-vue-next';

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
const loadingProgress = computed(() => store.loadingProgress || 0);

const placeholder = computed(() => 
  mode.value === 'dictionary' 
    ? 'Enter a word to define...' 
    : 'Enter a word to find synonyms...'
);

// Dynamic suggestions for landing page
const aiSuggestions = ref<string[]>([]);

// Generate dynamic suggestions on mount
onMounted(async () => {
  try {
    // Get random suggestions from API
    const response = await getSuggestions('a'); // Start with 'a' to get varied results
    if (response.length > 0) {
      // Take a random sample
      const shuffled = response.sort(() => 0.5 - Math.random());
      aiSuggestions.value = shuffled.slice(0, 4);
    }
  } catch (error) {
    // Fallback to some interesting words
    aiSuggestions.value = ['serendipity', 'ephemeral', 'luminous', 'eloquent'];
  }
});

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
  
  console.log('Searching for:', searchQuery.value);
  showSuggestions.value = false;
  await performSearch(searchQuery.value);
  await transitionToResults();
};

const selectSuggestion = async (suggestion: string) => {
  searchQuery.value = suggestion;
  showSuggestions.value = false;
  await handleSearch();
};

// const resetSearch = () => {
//   if (moved.value) {
//     store.reset();
//   }
// };
</script>