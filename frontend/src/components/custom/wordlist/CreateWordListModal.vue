<template>
  <Modal v-model="modelValue" :close-on-backdrop="false">
    <div class="w-full max-w-md mx-auto space-y-6 p-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold">Create Wordlist</h2>
        <Button 
          @click="closeModal" 
          variant="ghost" 
          size="sm" 
          class="h-6 w-6 p-0"
        >
          <X class="h-4 w-4" />
        </Button>
      </div>

      <!-- Form -->
      <div class="space-y-4">
        <!-- Name -->
        <div class="space-y-2">
          <label class="text-sm font-medium">
            Name <span class="text-destructive">*</span>
          </label>
          <Input
            v-model="form.name"
            placeholder="e.g., SAT Vocabulary, Business Terms..."
            class="w-full"
            :class="{ 'border-destructive': errors.name }"
          />
          <p v-if="errors.name" class="text-xs text-destructive">{{ errors.name }}</p>
        </div>

        <!-- Description -->
        <div class="space-y-2">
          <label class="text-sm font-medium">Description</label>
          <textarea
            v-model="form.description"
            placeholder="Brief description of this wordlist..."
            class="w-full px-3 py-2 bg-background border border-border rounded-md focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
            rows="3"
          />
        </div>

        <!-- Initial Words -->
        <div class="space-y-2">
          <label class="text-sm font-medium">Initial Words (Optional)</label>
          <textarea
            v-model="initialWordsText"
            placeholder="Enter words separated by commas or new lines..."
            class="w-full px-3 py-2 bg-background border border-border rounded-md focus:ring-2 focus:ring-primary focus:border-transparent resize-none"
            rows="4"
          />
          <p class="text-xs text-muted-foreground">
            You can add more words later through the upload feature.
          </p>
        </div>

        <!-- Tags -->
        <div class="space-y-2">
          <label class="text-sm font-medium">Tags</label>
          <div class="space-y-2">
            <Input
              v-model="newTag"
              placeholder="Add a tag..."
              class="w-full"
              @keydown.enter.prevent="addTag"
            />
            <div v-if="form.tags.length > 0" class="flex flex-wrap gap-1">
              <span
                v-for="tag in form.tags"
                :key="tag"
                class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-muted rounded-full"
              >
                {{ tag }}
                <button
                  @click="removeTag(tag)"
                  class="hover:text-destructive"
                >
                  <X class="h-3 w-3" />
                </button>
              </span>
            </div>
          </div>
        </div>

        <!-- Options -->
        <div class="space-y-3">
          <div class="flex items-center gap-2">
            <input
              id="is-public"
              v-model="form.isPublic"
              type="checkbox"
              class="rounded border-border"
            />
            <label for="is-public" class="text-sm">
              Make this wordlist public
            </label>
          </div>
          <p class="text-xs text-muted-foreground ml-6">
            Public wordlists can be discovered and used by other users.
          </p>
        </div>

        <!-- Word Preview -->
        <div v-if="parsedWords.length > 0" class="space-y-2">
          <div class="flex items-center justify-between">
            <label class="text-sm font-medium">
              Words to Add ({{ parsedWords.length }})
            </label>
            <Button
              @click="showAllWords = !showAllWords"
              variant="ghost"
              size="sm"
            >
              {{ showAllWords ? 'Show Less' : 'Show All' }}
            </Button>
          </div>
          
          <div class="max-h-32 overflow-y-auto bg-muted/30 rounded-md p-3">
            <div class="grid grid-cols-2 gap-1">
              <span
                v-for="word in displayedWords"
                :key="word"
                class="text-sm px-2 py-1 bg-background rounded"
              >
                {{ word }}
              </span>
            </div>
            
            <div v-if="!showAllWords && parsedWords.length > 10" class="text-center pt-2">
              <span class="text-xs text-muted-foreground">
                ... and {{ parsedWords.length - 10 }} more
              </span>
            </div>
          </div>
        </div>
      </div>

      <!-- Error Display -->
      <div v-if="error" class="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
        <p class="text-sm text-destructive">{{ error }}</p>
      </div>

      <!-- Loading State -->
      <div v-if="isCreating" class="space-y-2">
        <div class="flex items-center gap-2">
          <div class="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full"></div>
          <span class="text-sm">Creating wordlist...</span>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-2 justify-end pt-4 border-t">
        <Button variant="outline" @click="closeModal" :disabled="isCreating">
          Cancel
        </Button>
        <Button 
          @click="handleCreate" 
          :disabled="!canCreate || isCreating"
          class="min-w-[100px]"
        >
          <span v-if="isCreating">Creating...</span>
          <span v-else>Create Wordlist</span>
        </Button>
      </div>
    </div>
  </Modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { X } from 'lucide-vue-next';
import { Modal } from '@/components/custom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { WordList, CreateWordListRequest } from '@/types';

interface Props {
  modelValue: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  created: [wordlist: WordList];
}>();

// Component state
const form = ref({
  name: '',
  description: '',
  tags: [] as string[],
  isPublic: false,
});

const initialWordsText = ref('');
const newTag = ref('');
const showAllWords = ref(false);
const isCreating = ref(false);
const error = ref('');

const errors = ref({
  name: '',
});

// Computed properties
const modelValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const parsedWords = computed(() => {
  if (!initialWordsText.value.trim()) return [];
  
  // Parse words from comma-separated or newline-separated text
  const words = initialWordsText.value
    .split(/[,\n]/)
    .map(word => word.trim())
    .filter(word => word && word.length > 0)
    .filter((word, index, arr) => arr.indexOf(word) === index); // Remove duplicates
  
  return words;
});

const displayedWords = computed(() => {
  return showAllWords.value ? parsedWords.value : parsedWords.value.slice(0, 10);
});

const canCreate = computed(() => {
  return form.value.name.trim().length > 0 && !isCreating.value;
});

// Methods
const closeModal = () => {
  modelValue.value = false;
  resetForm();
};

const resetForm = () => {
  form.value = {
    name: '',
    description: '',
    tags: [],
    isPublic: false,
  };
  initialWordsText.value = '';
  newTag.value = '';
  showAllWords.value = false;
  error.value = '';
  errors.value = { name: '' };
};

const addTag = () => {
  const tag = newTag.value.trim().toLowerCase();
  if (tag && !form.value.tags.includes(tag)) {
    form.value.tags.push(tag);
    newTag.value = '';
  }
};

const removeTag = (tagToRemove: string) => {
  form.value.tags = form.value.tags.filter(tag => tag !== tagToRemove);
};

const validateForm = (): boolean => {
  errors.value = { name: '' };
  
  if (!form.value.name.trim()) {
    errors.value.name = 'Name is required';
    return false;
  }
  
  if (form.value.name.trim().length < 2) {
    errors.value.name = 'Name must be at least 2 characters';
    return false;
  }
  
  return true;
};

const handleCreate = async () => {
  if (!validateForm()) return;
  
  isCreating.value = true;
  error.value = '';
  
  try {
    const request: CreateWordListRequest = {
      name: form.value.name.trim(),
      description: form.value.description.trim() || undefined,
      words: parsedWords.value,
      tags: form.value.tags,
      is_public: form.value.isPublic,
    };
    
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    // Create mock wordlist response
    const mockWordlist: WordList = {
      id: `wl_${Date.now()}`,
      name: request.name,
      description: request.description || '',
      hash_id: `hash_${Date.now()}`,
      words: request.words.map(word => ({
        text: word,
        frequency: 1,
        selected_definitions: [],
        mastery_level: 'bronze' as const,
        temperature: 'cold' as const,
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
      })),
      total_words: request.words.length,
      unique_words: request.words.length,
      learning_stats: {
        total_reviews: 0,
        words_mastered: 0,
        average_ease_factor: 2.5,
        retention_rate: 0,
        streak_days: 0,
        last_study_date: null,
        study_time_minutes: 0,
      },
      last_accessed: null,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      metadata: {},
      tags: request.tags || [],
      is_public: request.is_public || false,
      owner_id: 'current_user',
    };
    
    // Emit the created event
    emit('created', mockWordlist);
    
    // Close modal
    closeModal();
    
  } catch (err) {
    console.error('Create wordlist error:', err);
    error.value = 'Failed to create wordlist. Please try again.';
  } finally {
    isCreating.value = false;
  }
};

// Watch for form changes to clear errors
watch(() => form.value.name, () => {
  if (errors.value.name) {
    errors.value.name = '';
  }
});
</script>

<style scoped>
/* Custom styles for the create form */
textarea {
  resize: vertical;
  min-height: 80px;
}
</style>