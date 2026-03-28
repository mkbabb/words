import { ref } from 'vue';
import { wordlistApi } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { useToast } from '@mkbabb/glass-ui';
import { useWordlistCache } from '@/composables/useWordlistCache';
import { useStores } from '@/stores';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { logger } from '@/utils/logger';
import type { WordList } from '@/types';

interface ActiveUpload {
    id: string;
    filename: string;
    status: string;
    progress: number;
}

export function useSidebarWordlistActions() {
    const auth = useAuthStore();
    const { toast } = useToast();
    const { fetchAllWordlists } = useWordlistCache();
    const { ui } = useStores();
    const searchBarStore = useSearchBarStore();
    const wordlistMode = useWordlistMode();

    // UI state
    const isDragging = ref(false);
    const showUploadModal = ref(false);
    const showCreateModal = ref(false);
    const pendingFiles = ref<File[]>([]);
    const activeUploads = ref<ActiveUpload[]>([]);

    // Delete dialog state
    const showDeleteDialog = ref(false);
    const wordlistToDelete = ref<WordList | null>(null);

    // Wordlists accessor (backed by store)
    const getWordlists = () => wordlistMode.allWordlists as WordList[];
    const setWordlists = (val: WordList[]) => {
        wordlistMode.allWordlists = val;
    };

    // Transform API response to frontend WordList format
    const transformWordlistFromAPI = (apiWordlist: any): WordList => ({
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
    });

    // File handling
    const handleFiles = async (files: File[]) => {
        if (files.length === 0) return;

        const validFiles = files.filter((file) => {
            const isValidType = file.name.match(/\.(txt|csv|json)$/i);
            const isValidSize = file.size <= 10 * 1024 * 1024;
            return isValidType && isValidSize;
        });

        if (validFiles.length === 0) {
            logger.error('No valid files selected');
            return;
        }

        if (validFiles.length === 1 && getWordlists().length > 0) {
            pendingFiles.value = validFiles;
            showUploadModal.value = true;
        } else {
            processFilesDirectly(validFiles);
        }
    };

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

    const processFilesDirectly = async (files: File[]) => {
        for (const file of files) {
            const uploadId = `upload_${Date.now()}_${Math.random()}`;

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

                    const result = await wordlistApi.uploadWordlist(file, {
                        owner_id: 'current_user',
                    });

                    upload.progress = 100;
                    upload.status = 'Complete';

                    const newWordlist = transformWordlistFromAPI(result.data);
                    const wordlists = getWordlists();
                    wordlists.unshift(newWordlist);
                    setWordlists([...wordlists]);

                    setTimeout(() => {
                        activeUploads.value = activeUploads.value.filter(
                            (u) => u.id !== uploadId,
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

    // Wordlist CRUD
    const loadWordlists = async () => {
        if (!auth.isAuthenticated) return;
        await fetchAllWordlists();
    };

    const handleWordlistSelect = async (wordlist: WordList) => {
        wordlistMode.setWordlist(wordlist.id);
        searchBarStore.setMode('wordlist');
        if (ui.sidebarOpen) {
            ui.toggleSidebar();
        }
    };

    const handleWordlistEdit = (wordlist: WordList) => {
        const newName = prompt('Enter new name for wordlist:', wordlist.name);
        if (newName && newName !== wordlist.name) {
            updateWordlistName(wordlist, newName);
        }
    };

    const updateWordlistName = async (wordlist: WordList, newName: string) => {
        try {
            await wordlistApi.updateWordlist(wordlist.id, { name: newName });
            const wordlists = getWordlists();
            const index = wordlists.findIndex((w) => w.id === wordlist.id);
            if (index >= 0) {
                wordlists[index].name = newName;
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
            const remaining = getWordlists().filter(
                (w) => w.id !== wordlistToDelete.value!.id,
            );
            setWordlists(remaining);

            if (wordlistMode.selectedWordlist === wordlistToDelete.value?.id) {
                wordlistMode.setWordlist(remaining[0]?.id || null);
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
            const wordlists = getWordlists();
            wordlists.unshift(newWordlist);
            setWordlists([...wordlists]);
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
        const wordlists = getWordlists();
        wordlists.unshift(wordlist);
        setWordlists([...wordlists]);
        wordlistMode.setWordlist(wordlist.id);
        searchBarStore.setMode('wordlist');
        if (ui.sidebarOpen) {
            ui.toggleSidebar();
        }
    };

    return {
        // UI state
        isDragging,
        showUploadModal,
        showCreateModal,
        pendingFiles,
        activeUploads,
        showDeleteDialog,
        wordlistToDelete,

        // File handling
        onDrop,
        onFileChange,

        // Wordlist CRUD
        loadWordlists,
        handleWordlistSelect,
        handleWordlistEdit,
        handleWordlistDelete,
        confirmDelete,
        handleWordlistDuplicate,

        // Upload/create handlers
        handleWordsUploaded,
        handleUploadCancel,
        handleWordlistCreated,
    };
}
