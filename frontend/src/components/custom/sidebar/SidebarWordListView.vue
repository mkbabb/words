<template>
    <div class="space-y-4 p-2">
        <!-- Search bar -->
        <div class="relative">
            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/50" />
            <input
                v-model="searchQuery"
                type="text"
                placeholder="Search wordlists..."
                class="w-full rounded-lg bg-background/60 dark:bg-white/[0.04] border border-border/30 pl-8 pr-3 py-1.5 text-sm placeholder:text-muted-foreground/50 focus:outline-none focus:ring-1 focus:ring-primary/30 transition-colors"
            />
        </div>

        <!-- Gradient separator -->
        <hr class="h-px border-0 divider-h" />

        <!-- All Wordlists -->
        <div v-if="isLoading" class="space-y-2">
            <div v-for="i in 3" :key="i" class="animate-pulse">
                <div class="h-16 rounded-md bg-muted/30"></div>
            </div>
        </div>

        <div v-else-if="wordlists.length === 0" class="py-8 text-center">
            <FileText class="mx-auto mb-3 h-12 w-12 text-muted-foreground/50" />
            <p class="text-muted-foreground">No wordlists found</p>
            <p class="mt-1 text-xs text-muted-foreground/70">
                Create your first wordlist to get started
            </p>
        </div>

        <div v-else-if="filteredWordlists.length === 0" class="py-4 text-center">
            <p class="text-sm text-muted-foreground">No matching wordlists</p>
        </div>

        <div v-else class="space-y-0">
            <template v-for="(wordlist, index) in filteredWordlists" :key="wordlist.id">
                <SidebarWordListItem
                    :wordlist="wordlist"
                    :is-selected="selectedWordlist === wordlist.id"
                    @select="handleWordlistSelect"
                    @edit="handleWordlistEdit"
                    @delete="handleWordlistDelete"
                    @duplicate="handleWordlistDuplicate"
                />
                <hr
                    v-if="index < filteredWordlists.length - 1"
                    class="my-0.5 border-0 h-px divider-h"
                />
            </template>
        </div>

        <!-- Gradient separator -->
        <hr class="h-px border-0 divider-h" />

        <!-- Add wordlist label -->
        <p class="text-micro font-medium uppercase tracking-wider text-muted-foreground/50">Add wordlist</p>

        <!-- File Upload Drop Zone -->
        <div
            @drop="onDrop"
            @dragover.prevent
            @dragenter.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            :class="[
                'cursor-pointer rounded-lg border-2 border-dashed p-4 text-center transition-all duration-200',
                isDragging
                    ? 'border-primary bg-primary/5'
                    : 'border-muted-foreground/30 hover:border-muted-foreground/50',
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
        <Button
            @click="showCreateModal = true"
            class="w-full"
            variant="outline"
            size="sm"
        >
            <Plus class="mr-2 h-4 w-4" />
            Create New Wordlist
        </Button>

        <!-- Processing Status (if there are any active uploads) -->
        <div v-if="activeUploads.length > 0" class="mb-4">
            <h3 class="mb-2 text-sm font-medium text-muted-foreground">
                Processing
            </h3>
            <div class="space-y-2">
                <div
                    v-for="upload in activeUploads"
                    :key="upload.id"
                    class="flex items-center justify-between rounded-md bg-muted/30 p-2"
                >
                    <div class="min-w-0 flex-1">
                        <p class="truncate text-sm font-medium">
                            {{ upload.filename }}
                        </p>
                        <p class="text-xs text-muted-foreground">
                            {{ upload.status }}
                        </p>
                    </div>
                    <div class="ml-2">
                        <div
                            class="h-1 w-12 overflow-hidden rounded-full bg-muted"
                        >
                            <div
                                class="h-full bg-primary transition-all duration-300"
                                :style="{ width: `${upload.progress}%` }"
                            />
                        </div>
                    </div>
                </div>
            </div>
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
import { useStores } from '@/stores';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { FileText, Plus, Search, Upload } from 'lucide-vue-next';
import { Button } from '@/components/ui/button';
import SidebarWordListItem from './SidebarWordListItem.vue';
import WordListUploadModal from '../wordlist/modals/WordListUploadModal.vue';
import CreateWordListModal from '../wordlist/modals/CreateWordListModal.vue';
import ConfirmDialog from '../ConfirmDialog.vue';
import type { WordList } from '@/types';
import { wordlistApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { useToast } from '@/components/ui/toast/use-toast';
import { logger } from '@/utils/logger';

const searchBarStore = useSearchBarStore();
const wordlistMode = useWordlistMode();
const auth = useAuthStore();
const { toast } = useToast();

// Access UI store for sidebar control
const { ui } = useStores();

// Component state
const fileInput = ref<HTMLInputElement>();
void fileInput; // bound via template ref="fileInput"
const isDragging = ref(false);
const showUploadModal = ref(false);
const showCreateModal = ref(false);
const pendingFiles = ref<File[]>([]);

// Dialog state
const showDeleteDialog = ref(false);
const wordlistToDelete = ref<WordList | null>(null);

// Shared wordlists from store
const wordlists = computed({
    get: () => wordlistMode.allWordlists as WordList[],
    set: (val: WordList[]) => { wordlistMode.allWordlists = val; },
});
const activeUploads = ref<
    Array<{
        id: string;
        filename: string;
        status: string;
        progress: number;
    }>
>([]);
const isLoading = computed(() => wordlistMode.wordlistsLoading);

// Search/filter
const searchQuery = ref('');
const filteredWordlists = computed(() => {
    const q = searchQuery.value.toLowerCase().trim();
    if (!q) return wordlists.value;
    return wordlists.value.filter(w => w.name.toLowerCase().includes(q));
});

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
    const validFiles = files.filter((file) => {
        const isValidType = file.name.match(/\.(txt|csv|json)$/i);
        const isValidSize = file.size <= 10 * 1024 * 1024; // 10MB
        return isValidType && isValidSize;
    });

    if (validFiles.length === 0) {
        logger.error('No valid files selected');
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
            const upload = activeUploads.value.find((u) => u.id === uploadId);
            if (upload) {
                upload.progress = 25;
                upload.status = 'Uploading...';

                // Upload to backend
                const result = await wordlistApi.uploadWordlist(file, {
                    owner_id: 'current_user',
                });

                upload.progress = 100;
                upload.status = 'Complete';

                // Transform backend response to frontend format
                const newWordlist = transformWordlistFromAPI(result.data);
                wordlists.value.unshift(newWordlist);

                // Remove from active uploads after a delay
                setTimeout(() => {
                    activeUploads.value = activeUploads.value.filter(
                        (u) => u.id !== uploadId
                    );
                }, 2000);
            }
        } catch (error) {
            logger.error('File processing error:', error);
            const upload = activeUploads.value.find((u) => u.id === uploadId);
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

// Load wordlists via shared store
const loadWordlists = async () => {
    if (!auth.isAuthenticated) return;
    await wordlistMode.fetchAllWordlists();

    // Auto-select first wordlist if none selected and wordlists exist
    if (!selectedWordlist.value && wordlists.value.length > 0) {
        wordlistMode.setWordlist(wordlists.value[0].id);
    }
};

const handleWordlistSelect = async (wordlist: WordList) => {
    wordlistMode.setWordlist(wordlist.id);
    // ✅ Use simple mode system - just change the mode
    searchBarStore.setMode('wordlist');

    // Close mobile sidebar if open (match SidebarLookupView pattern)
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
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
        const index = wordlists.value.findIndex((w) => w.id === wordlist.id);
        if (index >= 0) {
            wordlists.value[index].name = newName;
        }
    } catch (error) {
        logger.error('Failed to update wordlist name:', error);
        toast({
            title: 'Error',
            description: 'Failed to update wordlist name',
            variant: 'destructive',
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
        wordlists.value = wordlists.value.filter(
            (w) => w.id !== wordlistToDelete.value!.id
        );

        // Handle graceful fallback if deleted wordlist was selected
        if (selectedWordlist.value === wordlistToDelete.value?.id) {
            const firstWordlist = wordlists.value[0];
            wordlistMode.setWordlist(firstWordlist?.id || null);
        }

        toast({
            title: 'Success',
            description: `Wordlist "${wordlistToDelete.value.name}" has been deleted`,
        });
    } catch (error) {
        logger.error('Failed to delete wordlist:', error);
        toast({
            title: 'Error',
            description: 'Failed to delete wordlist',
            variant: 'destructive',
        });
    } finally {
        showDeleteDialog.value = false;
        wordlistToDelete.value = null;
    }
};

const handleWordlistDuplicate = async (wordlist: WordList) => {
    try {
        const words = wordlist.words.map((w) => w.word);
        const result = await wordlistApi.createWordlist({
            name: `${wordlist.name} (Copy)`,
            description: wordlist.description,
            words,
            tags: wordlist.tags,
            owner_id: 'current_user',
        });

        const newWordlist = transformWordlistFromAPI(result.data);
        wordlists.value.unshift(newWordlist);
    } catch (error) {
        logger.error('Failed to duplicate wordlist:', error);
    }
};

const handleWordsUploaded = (_words: string[]) => {
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

    // Close mobile sidebar if open
    if (ui.sidebarOpen) {
        ui.toggleSidebar();
    }
};

// Lifecycle
onMounted(() => {
    loadWordlists();
});
</script>

<style scoped>
/* Custom styles for drag and drop */
</style>
