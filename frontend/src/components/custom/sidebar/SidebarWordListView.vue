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
      @click="showUploadModal = true"
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

    <!-- Processing Status (if there are any active uploads) -->
    <div v-if="activeUploads.length > 0" class="mb-4">
      <h3 class="text-sm font-medium text-muted-foreground mb-2">Processing</h3>
      <div class="space-y-2">
        <div
          v-for="upload in activeUploads"
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
      </div>
    </div>

    <!-- All Wordlists -->
    <div v-if="isLoading" class="space-y-2">
      <div v-for="i in 3" :key="i" class="animate-pulse">
        <div class="h-16 bg-muted/30 rounded-md"></div>
      </div>
    </div>
    
    <div v-else-if="wordlists.length === 0" class="text-center py-8">
      <FileText class="h-12 w-12 mx-auto text-muted-foreground/50 mb-3" />
      <p class="text-muted-foreground">No wordlists found</p>
      <p class="text-xs text-muted-foreground/70 mt-1">
        Create your first wordlist to get started
      </p>
    </div>
    
    <div v-else class="space-y-2">
      <SidebarWordListItem
        v-for="wordlist in wordlists"
        :key="wordlist.id"
        :wordlist="wordlist"
        :is-selected="selectedWordlist === wordlist.id"
        @select="handleWordlistSelect"
        @edit="handleWordlistEdit"
        @delete="handleWordlistDelete"
        @duplicate="handleWordlistDuplicate"
      />
    </div>

    <!-- File Upload Modal -->
    <WordListUploadModal 
      v-model="showUploadModal"
      :uploaded-files="pendingFiles"
      @uploaded="handleWordsUploaded"
      @wordlists-updated="loadWordlists"
      @cancel="handleUploadCancel"
    />

    <!-- Create Wordlist Modal -->
    <CreateWordListModal
      v-model="showCreateModal"
      @created="handleWordlistCreated"
    />

    <ConfirmDialog
      v-model:open="showDeleteDialog"
      title="Delete Wordlist"
      :description="`Are you sure you want to delete &quot;${wordlistToDelete?.name}&quot;?`"
      message="This action cannot be undone. All words and progress will be permanently deleted."
      confirm-text="Delete"
      cancel-text="Cancel"
      :destructive="true"
      @confirm="confirmDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
// import { useStores } from '@/stores'; // Unused
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { 
  FileText, 
  Plus, 
  Upload
} from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import SidebarWordListItem from './SidebarWordListItem.vue';
import WordListUploadModal from '../wordlist/WordListUploadModal.vue';
import CreateWordListModal from '../wordlist/CreateWordListModal.vue';
import ConfirmDialog from '../ConfirmDialog.vue';
import type { WordList } from '@/types';
import { wordlistApi } from '@/api';
import { useToast } from '@/components/ui/toast/use-toast';

const searchBarStore = useSearchBarStore();
const wordlistMode = useWordlistMode();
const { toast } = useToast();

// Component state
const fileInput = ref<HTMLInputElement>();
const isDragging = ref(false);
const showUploadModal = ref(false);
const showCreateModal = ref(false);
const pendingFiles = ref<File[]>([]);

// Dialog state
const showDeleteDialog = ref(false);
const wordlistToDelete = ref<WordList | null>(null);

// Real data from API
const wordlists = ref<WordList[]>([]);
const activeUploads = ref<Array<{
  id: string;
  filename: string;
  status: string;
  progress: number;
}>>([]);
const isLoading = ref(false);

// Computed properties
const selectedWordlist = computed(() => wordlistMode.selectedWordlist);

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
  if (validFiles.length === 1 && wordlists.value.length > 0) {
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
      const upload = activeUploads.value.find(u => u.id === uploadId);
      if (upload) {
        upload.progress = 25;
        upload.status = 'Uploading...';
        
        // Upload to backend
        const result = await wordlistApi.uploadWordlist(file, {
          owner_id: 'current_user'
        });
        
        upload.progress = 100;
        upload.status = 'Complete';
        
        // Transform backend response to frontend format
        const newWordlist = transformWordlistFromAPI(result.data);
        wordlists.value.unshift(newWordlist);
        
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

// Transform API response to frontend WordList format
const transformWordlistFromAPI = (apiWordlist: any): WordList => {
  return {
    id: apiWordlist._id || apiWordlist.id,
    name: apiWordlist.name,
    description: apiWordlist.description,
    hash_id: apiWordlist.hash_id,
    words: apiWordlist.words || [],
    total_words: apiWordlist.total_words,
    unique_words: apiWordlist.unique_words,
    learning_stats: apiWordlist.learning_stats,
    last_accessed: apiWordlist.last_accessed,
    created_at: apiWordlist.created_at,
    updated_at: apiWordlist.updated_at,
    metadata: apiWordlist.metadata || {},
    tags: apiWordlist.tags || [],
    is_public: apiWordlist.is_public || false,
    owner_id: apiWordlist.owner_id,
  };
};

// Load wordlists from API
const loadWordlists = async () => {
  if (isLoading.value) return;
  
  isLoading.value = true;
  try {
    // Remove owner_id filter to get all wordlists from DB as requested
    const response = await wordlistApi.getWordlists({
      limit: 50
    });
    
    console.log('Loaded wordlists:', response);
    wordlists.value = response.items.map(transformWordlistFromAPI);
    
    // Auto-select first wordlist if none selected and wordlists exist
    if (!selectedWordlist && wordlists.value.length > 0) {
      console.log('Auto-selecting first wordlist:', wordlists.value[0].name, 'ID:', wordlists.value[0].id);
      wordlistMode.setWordlist(wordlists.value[0].id);
    } else {
      console.log('Wordlist selection state:', {
        selectedWordlist: selectedWordlist,
        wordlistsCount: wordlists.value.length,
        firstWordlistId: wordlists.value[0]?.id
      });
    }
  } catch (error) {
    console.error('Failed to load wordlists:', error);
  } finally {
    isLoading.value = false;
  }
};

const handleWordlistSelect = async (wordlist: WordList) => {
  wordlistMode.setWordlist(wordlist.id);
  // ✅ Use simple mode system - just change the mode
  searchBarStore.setMode('wordlist');
};

const handleWordlistEdit = (wordlist: WordList) => {
  // For now, just open a prompt to rename
  const newName = prompt('Enter new name for wordlist:', wordlist.name);
  if (newName && newName !== wordlist.name) {
    updateWordlistName(wordlist, newName);
  }
};

const updateWordlistName = async (wordlist: WordList, newName: string) => {
  try {
    await wordlistApi.updateWordlist(wordlist.id, { name: newName });
    
    // Update local data
    const index = wordlists.value.findIndex(w => w.id === wordlist.id);
    if (index >= 0) {
      wordlists.value[index].name = newName;
    }
  } catch (error) {
    console.error('Failed to update wordlist name:', error);
    toast({
      title: "Error",
      description: "Failed to update wordlist name",
      variant: "destructive",
    });
  }
};

const handleWordlistDelete = (wordlist: WordList) => {
  wordlistToDelete.value = wordlist;
  showDeleteDialog.value = true;
};

const confirmDelete = async () => {
  if (!wordlistToDelete.value) return;
  
  try {
    await wordlistApi.deleteWordlist(wordlistToDelete.value.id);
    wordlists.value = wordlists.value.filter(w => w.id !== wordlistToDelete.value!.id);
    
    // Handle graceful fallback if deleted wordlist was selected
    if (selectedWordlist.value === wordlistToDelete.value?.id) {
      const firstWordlist = wordlists.value[0];
      wordlistMode.setWordlist(firstWordlist?.id || null);
    }
    
    toast({
      title: "Success",
      description: `Wordlist "${wordlistToDelete.value.name}" has been deleted`,
    });
  } catch (error) {
    console.error('Failed to delete wordlist:', error);
    toast({
      title: "Error",
      description: "Failed to delete wordlist",
      variant: "destructive",
    });
  } finally {
    showDeleteDialog.value = false;
    wordlistToDelete.value = null;
  }
};

const handleWordlistDuplicate = async (wordlist: WordList) => {
  try {
    const words = wordlist.words.map(w => w.word);
    const result = await wordlistApi.createWordlist({
      name: `${wordlist.name} (Copy)`,
      description: wordlist.description,
      words,
      tags: wordlist.tags,
      owner_id: 'current_user'
    });
    
    const newWordlist = transformWordlistFromAPI(result.data);
    wordlists.value.unshift(newWordlist);
  } catch (error) {
    console.error('Failed to duplicate wordlist:', error);
  }
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

const handleWordlistCreated = async (wordlist: WordList) => {
  wordlists.value.unshift(wordlist);
  wordlistMode.setWordlist(wordlist.id);
  // ✅ Use simple mode system - just change the mode
  searchBarStore.setMode('wordlist');
};

// Lifecycle
onMounted(() => {
  loadWordlists();
});

</script>

<style scoped>
/* Custom styles for drag and drop */
</style>