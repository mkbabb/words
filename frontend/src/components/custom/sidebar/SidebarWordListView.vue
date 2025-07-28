<template>
  <div class="space-y-4 p-2">
    <!-- File Upload Drop Zone -->
    <div
      @drop="onDrop"
      @dragover.prevent
      @dragenter.prevent="isDragging = true"
      @dragleave.prevent="isDragging = false"
      :class="[
        'rounded-lg border-2 border-dashed p-4 text-center transition-all duration-200 cursor-pointer',
        isDragging ? 'border-primary bg-primary/5' : 'border-muted-foreground/30 hover:border-muted-foreground/50'
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
        <Upload class="mx-auto h-6 w-6 text-muted-foreground" />
        <div>
          <p class="text-sm font-medium">Quick Upload</p>
          <p class="text-xs text-muted-foreground">
            Drop files or click to browse
          </p>
        </div>
      </div>
    </div>

    <!-- Create New Wordlist Button -->
    <Button @click="showCreateModal = true" class="w-full" variant="outline" size="sm">
      <Plus class="h-4 w-4 mr-2" />
      Create New Wordlist
    </Button>

    <!-- Gradient separator -->
    <hr class="border-0 h-px bg-gradient-to-r from-transparent via-muted-foreground/20 to-transparent" />

    <!-- Accordion for wordlist sections -->
    <Accordion 
      type="multiple" 
      v-model="accordionValue"
      class="w-full"
    >
      <!-- My Wordlists -->
      <SidebarSection
        title="My Wordlists"
        value="my-wordlists"
        :items="userWordlists"
        :count="userWordlists.length"
        :icon="FileText"
        empty-message="No wordlists created yet"
      >
        <template #default="{ items }">
          <SidebarWordListItem
            v-for="wordlist in items"
            :key="wordlist.id"
            :wordlist="wordlist"
            :is-selected="selectedWordlist === wordlist.id"
            @select="handleWordlistSelect"
            @edit="handleWordlistEdit"
            @delete="handleWordlistDelete"
            @duplicate="handleWordlistDuplicate"
          />
        </template>
      </SidebarSection>

      <!-- Recent Wordlists -->
      <SidebarSection
        v-if="recentWordlists.length > 0"
        title="Recent"
        value="recent-wordlists"
        :items="recentWordlists"
        :count="recentWordlists.length"
        :icon="Clock"
        empty-message="No recent wordlists"
      >
        <template #default="{ items }">
          <SidebarWordListItem
            v-for="wordlist in items"
            :key="wordlist.id"
            :wordlist="wordlist"
            :is-selected="selectedWordlist === wordlist.id"
            @select="handleWordlistSelect"
            @edit="handleWordlistEdit"
            @delete="handleWordlistDelete"
          />
        </template>
      </SidebarSection>

      <!-- Public Wordlists -->
      <SidebarSection
        title="Browse Public"
        value="public-wordlists"
        :items="publicWordlists"
        :count="publicWordlists.length"
        :icon="Globe"
        empty-message="No public wordlists available"
      >
        <template #default="{ items }">
          <SidebarWordListItem
            v-for="wordlist in items"
            :key="wordlist.id"
            :wordlist="wordlist"
            :is-selected="selectedWordlist === wordlist.id"
            :is-public="true"
            @select="handleWordlistSelect"
            @duplicate="handleWordlistDuplicate"
          />
        </template>
      </SidebarSection>

      <!-- Processing Status (if there are any active uploads) -->
      <SidebarSection
        v-if="activeUploads.length > 0"
        title="Processing"
        value="processing"
        :items="activeUploads"
        :count="activeUploads.length"
        :icon="Loader2"
        empty-message="No active processing"
      >
        <template #default="{ items }">
          <div
            v-for="upload in items"
            :key="upload.id"
            class="flex items-center justify-between p-2 bg-muted/30 rounded-md"
          >
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium truncate">{{ upload.filename }}</p>
              <p class="text-xs text-muted-foreground">{{ upload.status }}</p>
            </div>
            <div class="ml-2">
              <div class="w-12 h-1 bg-muted rounded-full overflow-hidden">
                <div 
                  class="h-full bg-primary transition-all duration-300"
                  :style="{ width: `${upload.progress}%` }"
                />
              </div>
            </div>
          </div>
        </template>
      </SidebarSection>
    </Accordion>

    <!-- File Upload Modal -->
    <WordListUploadModal 
      v-model="showUploadModal"
      :uploaded-files="pendingFiles"
      @uploaded="handleWordsUploaded"
      @cancel="handleUploadCancel"
    />

    <!-- Create Wordlist Modal -->
    <CreateWordListModal
      v-model="showCreateModal"
      @created="handleWordlistCreated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useAppStore } from '@/stores';
import { 
  FileText, 
  Plus, 
  Upload, 
  Clock, 
  Globe, 
  Loader2 
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import { Accordion } from '@/components/ui/accordion';
import SidebarSection from './SidebarSection.vue';
import SidebarWordListItem from './SidebarWordListItem.vue';
import WordListUploadModal from '../wordlist/WordListUploadModal.vue';
import CreateWordListModal from '../wordlist/CreateWordListModal.vue';
import type { WordList } from '@/types';

const store = useAppStore();

// Component state
const fileInput = ref<HTMLInputElement>();
const isDragging = ref(false);
const showUploadModal = ref(false);
const showCreateModal = ref(false);
const pendingFiles = ref<File[]>([]);

// Mock data - replace with actual store data
const userWordlists = ref<WordList[]>([]);
const recentWordlists = ref<WordList[]>([]);
const publicWordlists = ref<WordList[]>([]);
const activeUploads = ref<Array<{
  id: string;
  filename: string;
  status: string;
  progress: number;
}>>([]);

// Computed properties
const accordionValue = computed({
  get: () => store.sidebarAccordionState.wordlist,
  set: (value: string[]) => {
    store.sidebarAccordionState.wordlist = value;
  },
});

const selectedWordlist = computed(() => store.selectedWordlist);

// Methods
const onDrop = (event: DragEvent) => {
  event.preventDefault();
  isDragging.value = false;
  
  const files = Array.from(event.dataTransfer?.files || []);
  handleFiles(files);
};

const onFileChange = (event: Event) => {
  const target = event.target as HTMLInputElement;
  const files = Array.from(target.files || []);
  handleFiles(files);
};

const handleFiles = async (files: File[]) => {
  if (files.length === 0) return;
  
  // Validate files
  const validFiles = files.filter(file => {
    const isValidType = file.name.match(/\.(txt|csv|json)$/i);
    const isValidSize = file.size <= 10 * 1024 * 1024; // 10MB
    return isValidType && isValidSize;
  });
  
  if (validFiles.length === 0) {
    console.error('No valid files selected');
    return;
  }
  
  // If single file and we have existing wordlists, show upload modal
  if (validFiles.length === 1 && userWordlists.value.length > 0) {
    pendingFiles.value = validFiles;
    showUploadModal.value = true;
  } else {
    // Multiple files or no existing wordlists - create new wordlists
    processFilesDirectly(validFiles);
  }
};

const processFilesDirectly = async (files: File[]) => {
  for (const file of files) {
    const uploadId = `upload_${Date.now()}_${Math.random()}`;
    
    // Add to active uploads
    activeUploads.value.push({
      id: uploadId,
      filename: file.name,
      status: 'Processing...',
      progress: 0,
    });
    
    try {
      // Simulate file processing
      const upload = activeUploads.value.find(u => u.id === uploadId);
      if (upload) {
        for (let i = 0; i <= 100; i += 20) {
          upload.progress = i;
          upload.status = i < 100 ? 'Processing...' : 'Complete';
          await new Promise(resolve => setTimeout(resolve, 200));
        }
        
        // Create wordlist from file
        const words = await extractWordsFromFile(file);
        const wordlistName = file.name.replace(/\.[^/.]+$/, ''); // Remove extension
        
        const newWordlist = await createWordlistFromWords(wordlistName, words);
        userWordlists.value.unshift(newWordlist);
        
        // Remove from active uploads after a delay
        setTimeout(() => {
          activeUploads.value = activeUploads.value.filter(u => u.id !== uploadId);
        }, 2000);
      }
    } catch (error) {
      console.error('File processing error:', error);
      const upload = activeUploads.value.find(u => u.id === uploadId);
      if (upload) {
        upload.status = 'Error';
        upload.progress = 0;
      }
    }
  }
};

const extractWordsFromFile = async (file: File): Promise<string[]> => {
  const text = await file.text();
  const extension = file.name.toLowerCase().split('.').pop();
  
  switch (extension) {
    case 'txt':
      return text.split('\n').map(line => line.trim()).filter(line => line);
    case 'csv':
      const lines = text.split('\n').filter(line => line.trim());
      const hasHeaders = lines[0]?.toLowerCase().includes('word');
      const dataLines = hasHeaders ? lines.slice(1) : lines;
      return dataLines.map(line => line.split(',')[0]?.trim()).filter(word => word);
    case 'json':
      const data = JSON.parse(text);
      if (Array.isArray(data)) {
        return data.map(item => typeof item === 'string' ? item : item.text || item.word).filter(Boolean);
      }
      return [];
    default:
      return [];
  }
};

const createWordlistFromWords = async (name: string, words: string[]): Promise<WordList> => {
  // Mock wordlist creation - replace with actual API call
  return {
    id: `wl_${Date.now()}`,
    name,
    description: `Imported from file`,
    hash_id: `hash_${Date.now()}`,
    words: words.map(word => ({
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
    total_words: words.length,
    unique_words: words.length,
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
    tags: [],
    is_public: false,
    owner_id: 'current_user',
  };
};

const handleWordlistSelect = (wordlist: WordList) => {
  store.selectWordlist(wordlist.id);
  
  // Add to recent if not already there
  const recentIndex = recentWordlists.value.findIndex(w => w.id === wordlist.id);
  if (recentIndex >= 0) {
    recentWordlists.value.splice(recentIndex, 1);
  }
  recentWordlists.value.unshift(wordlist);
  recentWordlists.value = recentWordlists.value.slice(0, 5);
};

const handleWordlistEdit = (wordlist: WordList) => {
  console.log('Edit wordlist:', wordlist.name);
  // Open edit modal
};

const handleWordlistDelete = async (wordlist: WordList) => {
  if (confirm(`Are you sure you want to delete "${wordlist.name}"?`)) {
    userWordlists.value = userWordlists.value.filter(w => w.id !== wordlist.id);
    recentWordlists.value = recentWordlists.value.filter(w => w.id !== wordlist.id);
    
    if (selectedWordlist.value === wordlist.id) {
      store.selectWordlist(null);
    }
  }
};

const handleWordlistDuplicate = async (wordlist: WordList) => {
  const duplicated = {
    ...wordlist,
    id: `wl_${Date.now()}`,
    name: `${wordlist.name} (Copy)`,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  };
  
  userWordlists.value.unshift(duplicated);
};

const handleWordsUploaded = (words: string[]) => {
  console.log('Words uploaded:', words.length);
  showUploadModal.value = false;
  pendingFiles.value = [];
};

const handleUploadCancel = () => {
  showUploadModal.value = false;
  pendingFiles.value = [];
};

const handleWordlistCreated = (wordlist: WordList) => {
  userWordlists.value.unshift(wordlist);
  store.selectWordlist(wordlist.id);
};

// Lifecycle
onMounted(() => {
  // Load initial wordlists - replace with actual API calls
  loadMockData();
});

const loadMockData = () => {
  // Mock data for development
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
  
  publicWordlists.value = [
    {
      id: 'pub_1',
      name: 'Common Academic Words',
      description: 'Frequently used academic vocabulary',
      hash_id: 'pub_hash_1',
      words: [],
      total_words: 570,
      unique_words: 570,
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
      created_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      updated_at: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString(),
      metadata: {},
      tags: ['academic', 'common'],
      is_public: true,
      owner_id: 'admin_user',
    },
  ];
};
</script>

<style scoped>
/* Custom styles for drag and drop */
</style>