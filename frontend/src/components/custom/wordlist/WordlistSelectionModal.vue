<template>
  <Modal v-model="modelValue" :close-on-backdrop="false">
    <div class="w-full max-w-lg mx-auto space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-xl font-semibold">Add Word to Wordlist</h2>
          <p class="text-sm text-muted-foreground mt-1">
            Adding "<span class="font-medium">{{ word }}</span>"
          </p>
        </div>
        <Button 
          @click="closeModal" 
          variant="ghost" 
          size="sm" 
          class="h-6 w-6 p-0"
        >
          <X class="h-4 w-4" />
        </Button>
      </div>

      <!-- Quick Create New Wordlist -->
      <div class="p-4 bg-muted/30 rounded-lg border-2 border-dashed border-muted-foreground/30">
        <div class="flex items-center gap-3">
          <Plus class="h-5 w-5 text-muted-foreground" />
          <div class="flex-1">
            <Input
              v-model="newWordlistName"
              placeholder="Create new wordlist..."
              class="bg-background"
              @keydown.enter="handleQuickCreate"
            />
          </div>
          <Button 
            @click="handleQuickCreate"
            :disabled="!newWordlistName.trim() || isCreating"
            size="sm"
          >
            Create
          </Button>
        </div>
      </div>

      <!-- Existing Wordlists -->
      <div class="space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="text-sm font-medium">Your Wordlists</h3>
          <span class="text-xs text-muted-foreground">
            {{ userWordlists.length }} available
          </span>
        </div>

        <div v-if="userWordlists.length === 0" class="text-center py-8 text-muted-foreground">
          <p class="text-sm">No wordlists yet.</p>
          <p class="text-xs mt-1">Create your first one above!</p>
        </div>

        <div v-else class="space-y-2 max-h-64 overflow-y-auto">
          <button
            v-for="wordlist in userWordlists"
            :key="wordlist.id"
            @click="handleAddToWordlist(wordlist)"
            :disabled="isWordAlreadyInList(wordlist) || isAdding"
            class="w-full flex items-center justify-between p-3 text-left rounded-lg border hover:bg-muted/50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            :class="{
              'border-primary bg-primary/5': isWordAlreadyInList(wordlist),
              'border-border': !isWordAlreadyInList(wordlist)
            }"
          >
            <div class="min-w-0 flex-1">
              <div class="flex items-center gap-2">
                <h4 class="font-medium text-sm truncate">{{ wordlist.name }}</h4>
                
                <!-- Already added indicator -->
                <div v-if="isWordAlreadyInList(wordlist)" class="flex items-center gap-1">
                  <Check class="h-3 w-3 text-primary" />
                  <span class="text-xs text-primary">Added</span>
                </div>
                
                <!-- Mastery indicators -->
                <div v-else class="flex items-center gap-0.5">
                  <div 
                    v-if="getMasteryStats(wordlist).gold > 0"
                    class="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-yellow-400 to-amber-600"
                    :title="`${getMasteryStats(wordlist).gold} mastered`"
                  />
                  <div 
                    v-if="getMasteryStats(wordlist).silver > 0"
                    class="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-gray-400 to-gray-600"
                    :title="`${getMasteryStats(wordlist).silver} familiar`"
                  />
                  <div 
                    v-if="getMasteryStats(wordlist).bronze > 0"
                    class="w-1.5 h-1.5 rounded-full bg-gradient-to-r from-orange-400 to-orange-600"
                    :title="`${getMasteryStats(wordlist).bronze} learning`"
                  />
                </div>
              </div>
              
              <div class="flex items-center gap-2 mt-1 text-xs text-muted-foreground">
                <span>{{ wordlist.unique_words }} words</span>
                <span>•</span>
                <span>{{ formatLastAccessed(wordlist.last_accessed) }}</span>
              </div>
            </div>
            
            <div class="ml-3 flex items-center">
              <Plus v-if="!isWordAlreadyInList(wordlist)" class="h-4 w-4 text-muted-foreground" />
            </div>
          </button>
        </div>
      </div>

      <!-- Frequency Tracking -->
      <div v-if="additionHistory.length > 0" class="space-y-2">
        <h3 class="text-sm font-medium">Addition History</h3>
        <div class="text-xs text-muted-foreground">
          This word has been added to {{ additionHistory.length }} wordlist(s) previously.
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isAdding || isCreating" class="space-y-2">
        <div class="flex items-center gap-2">
          <div class="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full"></div>
          <span class="text-sm">
            {{ isCreating ? 'Creating wordlist...' : 'Adding word...' }}
          </span>
        </div>
      </div>

      <!-- Error Display -->
      <div v-if="error" class="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
        <p class="text-sm text-destructive">{{ error }}</p>
      </div>

      <!-- Actions -->
      <div class="flex gap-2 justify-end pt-4 border-t">
        <Button variant="outline" @click="closeModal" :disabled="isAdding || isCreating">
          Cancel
        </Button>
      </div>
    </div>
  </Modal>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { X, Plus, Check } from 'lucide-vue-next';
import { Modal } from '@/components/custom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { WordList } from '@/types';
import { MasteryLevel, Temperature } from '@/types';

interface Props {
  modelValue: boolean;
  word: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'wordAdded': [wordlist: WordList, word: string];
}>();

// Component state
const newWordlistName = ref('');
const isAdding = ref(false);
const isCreating = ref(false);
const error = ref('');

// Mock data - replace with actual API calls
const userWordlists = ref<WordList[]>([]);
const additionHistory = ref<Array<{ wordlistId: string; addedAt: string }>>([]);

// Computed properties
const modelValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

// Methods
const closeModal = () => {
  modelValue.value = false;
  resetForm();
};

const resetForm = () => {
  newWordlistName.value = '';
  error.value = '';
};

const isWordAlreadyInList = (wordlist: WordList): boolean => {
  // Check if the current word is already in this wordlist
  return wordlist.words?.some(w => w.word?.toLowerCase() === props.word.toLowerCase()) || false;
};

const getMasteryStats = (wordlist: WordList) => {
  if (!wordlist.words || wordlist.words.length === 0) {
    return { bronze: 0, silver: 0, gold: 0 };
  }
  
  return wordlist.words.reduce((acc, word) => {
    acc[word.mastery_level]++;
    return acc;
  }, { bronze: 0, silver: 0, gold: 0 } as Record<MasteryLevel, number>);
};

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

const handleQuickCreate = async () => {
  const name = newWordlistName.value.trim();
  if (!name) return;

  isCreating.value = true;
  error.value = '';

  try {
    // Simulate API call to create wordlist
    await new Promise(resolve => setTimeout(resolve, 1000));

    // Create mock wordlist
    const newWordlist: WordList = {
      id: `wl_${Date.now()}`,
      name,
      description: `Created for "${props.word}"`,
      hash_id: `hash_${Date.now()}`,
      words: [{
        word: props.word,
        frequency: 1,
        selected_definition_ids: [],
        mastery_level: MasteryLevel.BRONZE,
        temperature: Temperature.COLD,
        review_data: {
          repetitions: 0,
          ease_factor: 2.5,
          interval: 1,
          next_review_date: new Date().toISOString(),
          last_review_date: null,
          lapse_count: 0,
          review_history: [],
        },
        last_visited: null,
        added_date: new Date().toISOString(),
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        notes: '',
        tags: [],
      }],
      total_words: 1,
      unique_words: 1,
      learning_stats: {
        total_reviews: 0,
        words_mastered: 0,
        average_ease_factor: 2.5,
        retention_rate: 0,
        streak_days: 0,
        last_study_date: null,
        study_time_minutes: 0,
      },
      last_accessed: new Date().toISOString(),
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: {},
      tags: [],
      is_public: false,
      owner_id: 'current_user',
    };

    // Add to local list
    userWordlists.value.unshift(newWordlist);
    
    // Emit success
    emit('wordAdded', newWordlist, props.word);
    
    // Close modal
    closeModal();

  } catch (err) {
    console.error('Create wordlist error:', err);
    error.value = 'Failed to create wordlist. Please try again.';
  } finally {
    isCreating.value = false;
  }
};

const handleAddToWordlist = async (wordlist: WordList) => {
  if (isWordAlreadyInList(wordlist)) return;

  isAdding.value = true;
  error.value = '';

  try {
    // Simulate API call to add word to wordlist
    await new Promise(resolve => setTimeout(resolve, 800));

    // Add word to local wordlist
    const newWord = {
      word: props.word,
      frequency: 1,
      selected_definition_ids: [],
      mastery_level: MasteryLevel.BRONZE,
      temperature: Temperature.COLD,
      review_data: {
        repetitions: 0,
        ease_factor: 2.5,
        interval: 1,
        next_review_date: new Date().toISOString(),
        last_review_date: null,
        lapse_count: 0,
        review_history: [],
      },
      last_visited: null,
      added_date: new Date().toISOString(),
      notes: '',
      tags: [],
    };

    if (!wordlist.words) wordlist.words = [];
    wordlist.words.push(newWord);
    wordlist.unique_words++;
    wordlist.total_words++;
    wordlist.last_accessed = new Date().toISOString();

    // Track addition history
    additionHistory.value.push({
      wordlistId: wordlist.id,
      addedAt: new Date().toISOString(),
    });

    // Emit success
    emit('wordAdded', wordlist, props.word);

    // Close modal after a brief delay to show success state
    setTimeout(() => {
      closeModal();
    }, 500);

  } catch (err) {
    console.error('Add to wordlist error:', err);
    error.value = 'Failed to add word to wordlist. Please try again.';
  } finally {
    isAdding.value = false;
  }
};

// Load initial data
onMounted(() => {
  // Mock loading user wordlists - replace with actual API call
  userWordlists.value = [
    {
      id: 'wl_1',
      name: 'SAT Vocabulary',
      description: 'Essential SAT words',
      hash_id: 'hash_1',
      words: [],
      total_words: 450,
      unique_words: 450,
      learning_stats: {
        total_reviews: 23,
        words_mastered: 12,
        average_ease_factor: 2.3,
        retention_rate: 0.85,
        streak_days: 5,
        last_study_date: new Date().toISOString(),
        study_time_minutes: 145,
      },
      last_accessed: new Date().toISOString(),
      created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date().toISOString(),
      metadata: {},
      tags: ['academic', 'test-prep'],
      is_public: false,
      owner_id: 'current_user',
    },
    {
      id: 'wl_2',
      name: 'Business English',
      description: 'Professional vocabulary',
      hash_id: 'hash_2',
      words: [],
      total_words: 120,
      unique_words: 120,
      learning_stats: {
        total_reviews: 8,
        words_mastered: 3,
        average_ease_factor: 2.5,
        retention_rate: 0.75,
        streak_days: 2,
        last_study_date: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        study_time_minutes: 67,
      },
      last_accessed: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      created_at: new Date(Date.now() - 14 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
      metadata: {},
      tags: ['business', 'professional'],
      is_public: false,
      owner_id: 'current_user',
    },
  ];
});
</script>

<style scoped>
/* Custom styles for the selection modal */
</style>