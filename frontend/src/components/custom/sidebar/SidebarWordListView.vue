<template>
    <div class="space-y-4 p-2">
        <!-- Search bar -->
        <div class="relative">
            <Search class="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground/70" />
            <input
                v-model="searchQuery"
                type="text"
                placeholder="Search wordlists..."
                class="w-full rounded-lg bg-background/96 dark:bg-background/85 border border-border/40 pl-8 pr-3 py-1.5 text-sm placeholder:text-muted-foreground/60 shadow-sm transition-[background-color,border-color,box-shadow] duration-200 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-primary/30"
            />
        </div>

        <!-- All Wordlists -->
        <div v-if="isLoading" class="space-y-2">
            <div v-for="i in 3" :key="i" class="animate-pulse">
                <div class="h-16 rounded-md border border-border/20 bg-background/96 shadow-sm"></div>
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

        <!-- File Upload Drop Zone -->
        <div
            @drop="onDrop"
            @dragover.prevent
            @dragenter.prevent="isDragging = true"
            @dragleave.prevent="isDragging = false"
            :class="[
                'cursor-pointer rounded-lg border-2 border-dashed border-border/30 bg-background/96 p-4 text-center shadow-sm transition-[background-color,border-color,box-shadow,transform] duration-250 ease-apple-spring',
                isDragging
                    ? 'border-primary bg-primary/5 shadow-md'
                    : 'hover:-translate-y-0.5 hover:border-muted-foreground/50 hover:bg-background hover:shadow-md',
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
                    class="flex items-center justify-between rounded-md border border-border/30 bg-background/96 p-2 shadow-sm"
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
                                class="h-full bg-primary"
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
            :description="`Are you sure you want to delete &quot;${wordlistToDelete?.name}&quot;? This action cannot be undone.`"
            confirm-label="Delete"
            :destructive="true"
            @confirm="confirmDelete"
        />
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { FileText, Plus, Search, Upload } from 'lucide-vue-next';
import { Button } from '@mkbabb/glass-ui';
import SidebarWordListItem from './SidebarWordListItem.vue';
import WordListUploadModal from '../wordlist/modals/WordListUploadModal.vue';
import CreateWordListModal from '../wordlist/modals/CreateWordListModal.vue';
import { ConfirmDialog } from '@mkbabb/glass-ui';
import type { WordList } from '@/types';
import { useSidebarWordlistActions } from './composables/useSidebarWordlistActions';

const wordlistMode = useWordlistMode();

const actions = useSidebarWordlistActions();

const {
    isDragging,
    showUploadModal,
    showCreateModal,
    pendingFiles,
    activeUploads,
    showDeleteDialog,
    wordlistToDelete,
    onDrop,
    onFileChange,
    loadWordlists,
    handleWordlistSelect,
    handleWordlistEdit,
    handleWordlistDelete,
    confirmDelete,
    handleWordlistDuplicate,
    handleWordsUploaded,
    handleUploadCancel,
    handleWordlistCreated,
} = actions;

// Component state
const fileInput = ref<HTMLInputElement>();
void fileInput; // bound via template ref="fileInput"

// Shared wordlists from store
const wordlists = computed({
    get: () => wordlistMode.allWordlists as WordList[],
    set: (val: WordList[]) => { wordlistMode.allWordlists = val; },
});
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

// Lifecycle
onMounted(() => {
    loadWordlists();
});
</script>

<style scoped>
/* Custom styles for drag and drop */
</style>
