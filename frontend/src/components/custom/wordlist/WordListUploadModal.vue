<template>
  <Modal v-model="modelValue" :close-on-backdrop="false">
    <div class="w-full max-w-md mx-auto space-y-6 p-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold">Upload Words</h2>
        <Button 
          @click="closeModal" 
          variant="ghost" 
          size="sm" 
          class="h-6 w-6 p-0"
        >
          <X class="h-4 w-4" />
        </Button>
      </div>

      <!-- File Upload Area -->
      <div class="space-y-4">
        <div
          @drop="onDrop"
          @dragover.prevent
          @dragenter.prevent
          :class="[
            'border-2 border-dashed rounded-lg p-6 text-center transition-colors cursor-pointer',
            isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/25 hover:border-muted-foreground/50'
          ]"
          @click="fileInput?.click()"
        >
          <input
            ref="fileInput"
            type="file"
            accept=".txt,.csv,.json"
            @change="onFileChange"
            class="hidden"
            multiple
          />
          
          <div class="space-y-2">
            <Upload class="h-8 w-8 mx-auto text-muted-foreground" />
            <div>
              <p class="font-medium">Drop files here or click to browse</p>
              <p class="text-sm text-muted-foreground">
                Supports .txt, .csv, and .json files
              </p>
            </div>
          </div>
        </div>

        <!-- File Format Instructions -->
        <div class="text-xs text-muted-foreground space-y-1">
          <p><strong>Supported formats:</strong></p>
          <ul class="list-disc list-inside space-y-0.5 ml-2">
            <li><strong>.txt:</strong> One word per line</li>
            <li><strong>.csv:</strong> word,frequency,notes (headers optional)</li>
            <li><strong>.json:</strong> Array of words or word objects</li>
          </ul>
        </div>
      </div>

      <!-- File Preview -->
      <div v-if="uploadedFiles.length > 0" class="space-y-3">
        <h3 class="font-medium">Uploaded Files</h3>
        <div class="space-y-2 max-h-32 overflow-y-auto">
          <div
            v-for="file in uploadedFiles"
            :key="file.name"
            class="flex items-center justify-between p-2 bg-muted/50 rounded-md"
          >
            <div class="flex items-center gap-2">
              <FileText class="h-4 w-4" />
              <span class="text-sm">{{ file.name }}</span>
            </div>
            <Button
              @click="removeFile(file)"
              variant="ghost"
              size="sm"
              class="h-6 w-6 p-0"
            >
              <X class="h-3 w-3" />
            </Button>
          </div>
        </div>
      </div>

      <!-- Parsed Words Preview -->
      <div v-if="parsedWords.length > 0" class="space-y-3">
        <div class="flex items-center justify-between">
          <h3 class="font-medium">
            Words Found ({{ parsedWords.length }})
          </h3>
          <Button
            @click="showAllWords = !showAllWords"
            variant="ghost"
            size="sm"
          >
            {{ showAllWords ? 'Show Less' : 'Show All' }}
          </Button>
        </div>
        
        <div class="max-h-40 overflow-y-auto bg-muted/30 rounded-md p-3">
          <div class="grid grid-cols-1 gap-1">
            <div
              v-for="(word, index) in displayedWords"
              :key="index"
              class="flex justify-between items-center py-1"
            >
              <span class="text-sm">{{ word.text }}</span>
              <div class="flex items-center gap-2 text-xs text-muted-foreground">
                <span v-if="word.frequency > 1">{{ word.frequency }}x</span>
                <span v-if="word.notes" class="bg-muted px-1 rounded">
                  {{ word.notes }}
                </span>
              </div>
            </div>
          </div>
          
          <div v-if="!showAllWords && parsedWords.length > 10" class="text-center pt-2">
            <span class="text-xs text-muted-foreground">
              ... and {{ parsedWords.length - 10 }} more
            </span>
          </div>
        </div>
      </div>

      <!-- Wordlist Selection -->
      <div v-if="parsedWords.length > 0" class="space-y-3">
        <div class="space-y-2">
          <label class="text-sm font-medium">Add to Wordlist</label>
          <select
            v-model="selectedWordlistId"
            class="w-full px-3 py-2 bg-background border border-border rounded-md focus:ring-2 focus:ring-primary focus:border-transparent"
          >
            <option value="">Select a wordlist...</option>
            <option
              v-for="wordlist in availableWordlists"
              :key="wordlist.id"
              :value="wordlist.id"
            >
              {{ wordlist.name }} ({{ wordlist.unique_words }} words)
            </option>
          </select>
        </div>

        <!-- Create New Wordlist Option -->
        <div class="space-y-2">
          <div class="flex items-center gap-2">
            <input
              id="create-new"
              v-model="createNew"
              type="checkbox"
              class="rounded border-border"
            />
            <label for="create-new" class="text-sm">Create new wordlist</label>
          </div>
          
          <div v-if="createNew" class="space-y-2">
            <Input
              v-model="newWordlistName"
              placeholder="Wordlist name..."
              class="w-full"
            />
            <Input
              v-model="newWordlistDescription"
              placeholder="Description (optional)..."
              class="w-full"
            />
          </div>
        </div>
      </div>

      <!-- Error Display -->
      <div v-if="error" class="p-3 bg-destructive/10 border border-destructive/20 rounded-md">
        <p class="text-sm text-destructive">{{ error }}</p>
      </div>

      <!-- Loading State -->
      <div v-if="isUploading" class="space-y-2">
        <div class="flex items-center gap-2">
          <div class="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full"></div>
          <span class="text-sm">{{ uploadStatus }}</span>
        </div>
        <div class="w-full bg-muted rounded-full h-2">
          <div 
            class="bg-primary h-2 rounded-full transition-all duration-300"
            :style="{ width: `${uploadProgress}%` }"
          ></div>
        </div>
      </div>

      <!-- Actions -->
      <div class="flex gap-2 justify-end pt-4 border-t">
        <Button variant="outline" @click="closeModal" :disabled="isUploading">
          Cancel
        </Button>
        <Button 
          @click="handleUpload" 
          :disabled="!canUpload || isUploading"
          class="min-w-[100px]"
        >
          <span v-if="isUploading">Uploading...</span>
          <span v-else>Add Words</span>
        </Button>
      </div>
    </div>
  </Modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { Upload, X, FileText } from 'lucide-vue-next';
import { Modal } from '@/components/custom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { WordList } from '@/types';

interface Props {
  modelValue: boolean;
  wordlistId?: string;
}

interface ParsedWord {
  text: string;
  frequency: number;
  notes?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  'update:modelValue': [value: boolean];
  uploaded: [words: string[]];
}>();

// Component state
const fileInput = ref<HTMLInputElement>();
const uploadedFiles = ref<File[]>([]);
const parsedWords = ref<ParsedWord[]>([]);
const selectedWordlistId = ref(props.wordlistId || '');
const createNew = ref(false);
const newWordlistName = ref('');
const newWordlistDescription = ref('');
const showAllWords = ref(false);
const isDragging = ref(false);
const isUploading = ref(false);
const uploadProgress = ref(0);
const uploadStatus = ref('');
const error = ref('');

// Mock data - replace with actual store data
const availableWordlists = ref<WordList[]>([]);

// Computed properties
const modelValue = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
});

const displayedWords = computed(() => {
  return showAllWords.value ? parsedWords.value : parsedWords.value.slice(0, 10);
});

const canUpload = computed(() => {
  return parsedWords.value.length > 0 && 
         (selectedWordlistId.value || (createNew.value && newWordlistName.value.trim()));
});

// Methods
const closeModal = () => {
  modelValue.value = false;
  resetState();
};

const resetState = () => {
  uploadedFiles.value = [];
  parsedWords.value = [];
  selectedWordlistId.value = props.wordlistId || '';
  createNew.value = false;
  newWordlistName.value = '';
  newWordlistDescription.value = '';
  showAllWords.value = false;
  error.value = '';
  uploadProgress.value = 0;
};

const onDrop = (event: DragEvent) => {
  event.preventDefault();
  isDragging.value = false;
  
  const files = Array.from(event.dataTransfer?.files || []);
  addFiles(files);
};

const onFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const files = Array.from(target.files || []);
  addFiles(files);
};

const addFiles = async (files: File[]) => {
  error.value = '';
  
  for (const file of files) {
    if (file.size > 10 * 1024 * 1024) { // 10MB limit
      error.value = `File ${file.name} is too large (max 10MB)`;
      continue;
    }
    
    if (!file.name.match(/\.(txt|csv|json)$/i)) {
      error.value = `File ${file.name} has unsupported format`;
      continue;
    }
    
    uploadedFiles.value.push(file);
    await parseFile(file);
  }
};

const parseFile = async (file: File): Promise<void> => {
  try {
    const text = await file.text();
    const extension = file.name.toLowerCase().split('.').pop();
    
    let newWords: ParsedWord[] = [];
    
    switch (extension) {
      case 'txt':
        newWords = parseTxtFile(text);
        break;
      case 'csv':
        newWords = parseCsvFile(text);
        break;
      case 'json':
        newWords = parseJsonFile(text);
        break;
    }
    
    // Merge with existing parsed words, combining frequencies
    const wordMap = new Map<string, ParsedWord>();
    
    // Add existing words
    parsedWords.value.forEach(word => {
      wordMap.set(word.text.toLowerCase(), word);
    });
    
    // Add new words
    newWords.forEach(word => {
      const key = word.text.toLowerCase();
      if (wordMap.has(key)) {
        const existing = wordMap.get(key)!;
        existing.frequency += word.frequency;
        if (word.notes && !existing.notes) {
          existing.notes = word.notes;
        }
      } else {
        wordMap.set(key, word);
      }
    });
    
    parsedWords.value = Array.from(wordMap.values())
      .sort((a, b) => b.frequency - a.frequency);
    
  } catch (err) {
    console.error('File parsing error:', err);
    error.value = `Failed to parse ${file.name}`;
  }
};

const parseTxtFile = (text: string): ParsedWord[] => {
  return text
    .split('\n')
    .map(line => line.trim())
    .filter(line => line && !line.startsWith('#'))
    .map(word => ({ text: word, frequency: 1 }));
};

const parseCsvFile = (text: string): ParsedWord[] => {
  const lines = text.split('\n').filter(line => line.trim());
  const hasHeaders = lines[0]?.toLowerCase().includes('word');
  const dataLines = hasHeaders ? lines.slice(1) : lines;
  
  return dataLines.map(line => {
    const [word, frequency = '1', notes = ''] = line.split(',').map(s => s.trim());
    return {
      text: word,
      frequency: parseInt(frequency) || 1,
      notes: notes || undefined
    };
  }).filter(item => item.text);
};

const parseJsonFile = (text: string): ParsedWord[] => {
  const data = JSON.parse(text);
  
  if (Array.isArray(data)) {
    return data.map(item => {
      if (typeof item === 'string') {
        return { text: item, frequency: 1 };
      } else if (typeof item === 'object' && item.text) {
        return {
          text: item.text,
          frequency: item.frequency || 1,
          notes: item.notes
        };
      }
      return null;
    }).filter(Boolean) as ParsedWord[];
  }
  
  throw new Error('JSON must be an array');
};

const removeFile = (fileToRemove: File) => {
  uploadedFiles.value = uploadedFiles.value.filter(file => file !== fileToRemove);
  
  // Re-parse remaining files
  parsedWords.value = [];
  uploadedFiles.value.forEach(file => parseFile(file));
};

const handleUpload = async () => {
  if (!canUpload.value) return;
  
  isUploading.value = true;
  uploadProgress.value = 0;
  uploadStatus.value = 'Preparing upload...';
  
  try {
    // Simulate upload progress
    for (let i = 0; i <= 100; i += 10) {
      uploadProgress.value = i;
      uploadStatus.value = i < 100 ? 'Uploading words...' : 'Finalizing...';
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    
    // Extract just the word texts for the API
    const words = parsedWords.value.map(w => w.text);
    
    // Emit the upload event
    emit('uploaded', words);
    
    // Close modal
    closeModal();
    
  } catch (err) {
    console.error('Upload error:', err);
    error.value = 'Failed to upload words. Please try again.';
  } finally {
    isUploading.value = false;
  }
};

// Watch for prop changes
watch(() => props.wordlistId, (newId) => {
  selectedWordlistId.value = newId || '';
});
</script>

<style scoped>
/* Custom styles for drag and drop */
</style>