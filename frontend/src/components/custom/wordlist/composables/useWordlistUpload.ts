import { ref } from 'vue';
import { wordlistApi } from '@/api';
import { useToast } from '@/components/ui/toast/use-toast';
import { logger } from '@/utils/logger';
import type { WordList } from '@/types';
import type { ParsedWord } from './useWordlistFileParser';

interface UseWordlistUploadOptions {
    onComplete: (words: string[]) => void;
    onWordlistsUpdated: () => void;
    onClose: () => void;
}

/**
 * Handles upload logic including SSE streaming for wordlist creation.
 */
export function useWordlistUpload(options: UseWordlistUploadOptions) {
    const { onComplete, onWordlistsUpdated, onClose } = options;
    const { toast } = useToast();

    const isUploading = ref(false);
    const uploadProgress = ref(0);
    const uploadStatus = ref('');
    const uploadStage = ref('');
    const uploadStageDefinitions = ref<
        Array<{ progress: number; label: string; description: string }>
    >([]);
    const uploadCategory = ref('');
    const error = ref('');

    // Wordlist state
    const wordlists = ref<WordList[]>([]);
    const isLoadingWordlist = ref(false);

    const loadWordlists = async () => {
        try {
            isLoadingWordlist.value = true;
            const response = await wordlistApi.getWordlists();
            wordlists.value = response.items;
            return response.items;
        } catch (err) {
            logger.error('Failed to load wordlists:', err);
            toast({
                title: 'Error',
                description: 'Failed to load wordlists',
                variant: 'destructive',
            });
            return [];
        } finally {
            isLoadingWordlist.value = false;
        }
    };

    const handleUpload = async (
        parsedWords: ParsedWord[],
        uploadMode: 'new' | 'existing',
        selectedWordlistId: string,
        newWordlistName: string,
        newWordlistDescription: string
    ) => {
        isUploading.value = true;
        uploadProgress.value = 0;
        uploadStatus.value = 'Preparing upload...';
        error.value = '';

        try {
            const words = parsedWords.map((w) => w.text);

            if (uploadMode === 'new') {
                // Create new wordlist with streaming
                uploadStatus.value = 'Creating new wordlist...';
                uploadStage.value = 'initializing';
                uploadCategory.value = 'wordlist_creation';

                // Create FormData for file upload
                const fileName = newWordlistName.trim() || 'wordlist';
                const blob = new Blob([words.join('\n')], {
                    type: 'text/plain',
                });
                const file = new File([blob], `${fileName}.txt`, {
                    type: 'text/plain',
                });

                const response = await wordlistApi.uploadWordlistStream(
                    file,
                    {
                        name: newWordlistName.trim() || undefined,
                        description: newWordlistDescription.trim() || undefined,
                    },
                    (stage, progress, message) => {
                        uploadStage.value = stage;
                        uploadProgress.value = progress;
                        uploadStatus.value = message || `${stage}...`;

                        // Check if this is completion via progress callback
                        if (stage === 'COMPLETE' || progress === 100) {
                            setTimeout(async () => {
                                await loadWordlists();
                                onComplete(words);
                                onWordlistsUpdated();
                                onClose();
                            }, 500);
                        }
                    },
                    (category, stages) => {
                        uploadCategory.value = category;
                        uploadStageDefinitions.value = stages;
                    }
                );

                if (response) {
                    await loadWordlists();
                    onComplete(words);
                    onWordlistsUpdated();
                }
            } else {
                // Add to existing wordlist
                uploadStatus.value = 'Adding words to wordlist...';
                uploadProgress.value = 50;

                await wordlistApi.addWords(selectedWordlistId, words);
                uploadProgress.value = 100;

                await loadWordlists();
                onComplete(words);
                onWordlistsUpdated();
            }

            uploadStatus.value = 'Complete!';
            onClose();
        } catch (err) {
            logger.error('Upload error:', err);
            error.value =
                err instanceof Error
                    ? err.message
                    : 'Failed to upload words. Please try again.';
        } finally {
            isUploading.value = false;
        }
    };

    const resetUploadState = () => {
        uploadProgress.value = 0;
        uploadStatus.value = '';
        uploadStage.value = '';
        uploadStageDefinitions.value = [];
        uploadCategory.value = '';
        error.value = '';
    };

    return {
        // State
        isUploading,
        uploadProgress,
        uploadStatus,
        uploadStage,
        uploadStageDefinitions,
        uploadCategory,
        error,
        wordlists,
        isLoadingWordlist,

        // Methods
        loadWordlists,
        handleUpload,
        resetUploadState,
    };
}
