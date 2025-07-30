<template>
  <Modal v-model="modelValue" :close-on-backdrop="false">
    <div class="w-full max-w-md mx-auto space-y-6 p-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold">Add "{{ word }}" to Wordlist</h2>
        <Button 
          @click="closeModal" 
          variant="ghost" 
          size="sm" 
          class="h-6 w-6 p-0"
        >
          <X class="h-4 w-4" />
        </Button>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="flex items-center justify-center py-8">
        <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
      </div>

      <!-- Content -->
      <div v-else class="space-y-4">
        <!-- Create New Wordlist Option -->
        <div class="flex items-center justify-between p-3 border border-border rounded-lg hover:bg-muted/30 transition-colors">
          <div class="flex items-center gap-3">
            <Plus class="h-5 w-5 text-primary" />
            <span class="font-medium">Create New Wordlist</span>
          </div>
          <Button 
            @click="showCreateModal = true"
            variant="outline" 
            size="sm"
          >
            Create
          </Button>
        </div>

        <!-- Existing Wordlists -->
        <div v-if="wordlists.length > 0" class="space-y-2">
          <h3 class="text-sm font-medium text-muted-foreground">Your Wordlists</h3>
          <div class="max-h-64 overflow-y-auto space-y-2">
            <div
              v-for="wordlist in wordlists"
              :key="wordlist.id"
              class="flex items-center justify-between p-3 border border-border rounded-lg hover:bg-muted/30 transition-colors"
            >
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="font-medium truncate">{{ wordlist.name }}</span>
                  <span 
                    v-if="isWordInWordlist(wordlist)"
                    class="inline-flex items-center px-2 py-0.5 rounded-full text-xs bg-primary/10 text-primary border border-primary/20"
                  >
                    Added {{ getWordFrequency(wordlist) }}x
                  </span>
                </div>
                <div class="text-xs text-muted-foreground mt-1">
                  {{ wordlist.unique_words }} words
                </div>
              </div>
              <Button 
                @click="addToWordlist(wordlist)"
                :variant="isWordInWordlist(wordlist) ? 'outline' : 'default'"
                size="sm"
                :disabled="isAdding"
              >
                <Loader2 v-if="isAdding" class="h-3 w-3 animate-spin mr-2" />
                {{ isWordInWordlist(wordlist) ? 'Add Again' : 'Add' }}
              </Button>
            </div>
          </div>
        </div>

        <!-- Empty State -->
        <div v-else class="text-center py-8">
          <FileText class="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
          <p class="text-muted-foreground">No wordlists found</p>
          <p class="text-xs text-muted-foreground/70 mt-1">
            Create your first wordlist to get started
          </p>
        </div>
      </div>

      <!-- Create Wordlist Modal -->
      <CreateWordListModal
        v-model="showCreateModal"
        :initial-words="[word]"
        @created="handleWordlistCreated"
      />
    </div>
  </Modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { 
  X, 
  Plus, 
  FileText, 
  Loader2
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import Modal from '@/components/custom/Modal.vue';
import CreateWordListModal from '../../wordlist/CreateWordListModal.vue';
import type { WordList } from '@/types';
import { MasteryLevel, Temperature } from '@/types';
import { wordlistApi } from '@/utils/api';

interface Props {
  modelValue: boolean;
  word: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  'added': [wordlistName: string];
}>();

// Component state
const isLoading = ref(false);
const isAdding = ref(false);
const showCreateModal = ref(false);
const wordlists = ref<WordList[]>([]);

// Computed properties
const modelValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

// Methods
const closeModal = () => {
  modelValue.value = false;
};

const loadWordlists = async () => {
  isLoading.value = true;
  try {
    const response = await wordlistApi.getWordlists({
      limit: 50
    });
    
    wordlists.value = response.items.map((item: any) => ({
      id: item._id || item.id,
      name: item.name,
      description: item.description,
      hash_id: item.hash_id,
      words: item.words || [],
      total_words: item.total_words,
      unique_words: item.unique_words,
      learning_stats: item.learning_stats,
      last_accessed: item.last_accessed,
      created_at: item.created_at,
      updated_at: item.updated_at,
      metadata: item.metadata || {},
      tags: item.tags || [],
      is_public: item.is_public || false,
      owner_id: item.owner_id,
    }));
  } catch (error) {
    console.error('Failed to load wordlists:', error);
  } finally {
    isLoading.value = false;
  }
};

const isWordInWordlist = (wordlist: WordList): boolean => {
  return wordlist.words.some(w => w.word.toLowerCase() === props.word.toLowerCase());
};

const getWordFrequency = (wordlist: WordList): number => {
  const wordItem = wordlist.words.find(w => w.text.toLowerCase() === props.word.toLowerCase());
  return wordItem?.frequency || 0;
};

const addToWordlist = async (wordlist: WordList) => {
  isAdding.value = true;
  try {
    await wordlistApi.addWords(wordlist.id, [props.word]);
    
    // Update local wordlist data
    const wordlistIndex = wordlists.value.findIndex(w => w.id === wordlist.id);
    if (wordlistIndex >= 0) {
      const existingWordIndex = wordlists.value[wordlistIndex].words.findIndex(
        w => w.word.toLowerCase() === props.word.toLowerCase()
      );
      
      if (existingWordIndex >= 0) {
        // Increment frequency
        wordlists.value[wordlistIndex].words[existingWordIndex].frequency++;
      } else {
        // Add new word
        wordlists.value[wordlistIndex].words.push({
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
        });
        wordlists.value[wordlistIndex].unique_words++;
      }
      wordlists.value[wordlistIndex].total_words++;
    }
    
    emit('added', wordlist.name);
  } catch (error) {
    console.error('Failed to add word to wordlist:', error);
  } finally {
    isAdding.value = false;
  }
};

const handleWordlistCreated = (wordlist: WordList) => {
  wordlists.value.unshift(wordlist);
  showCreateModal.value = false;
  emit('added', wordlist.name);
};

// Watch for modal opening
watch(() => props.modelValue, (isOpen) => {
  if (isOpen) {
    loadWordlists();
  }
});

// Load wordlists on mount if modal is already open
onMounted(() => {
  if (props.modelValue) {
    loadWordlists();
  }
});
</script>

<style scoped>
/* Additional styles if needed */
</style>