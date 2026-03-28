import { computed, ref, watch, onMounted, type Ref } from 'vue';
import { useSlugGeneration } from '@/composables/useSlugGeneration';
import { useWordlistFileParser, type ParsedWord } from '../../composables/useWordlistFileParser';
import { useWordlistReconcilePreview, type ReviewCandidate } from '../../composables/useWordlistReconcilePreview';
import { useWordlistUpload } from '../../composables/useWordlistUpload';

export type UploadStep = 'dropzone' | 'review';
export type UploadMode = 'new' | 'existing';

interface UseUploadWorkflowOptions {
    modelValue: Ref<boolean>;
    wordlistId: Ref<string | undefined>;
    onUploaded: (words: string[]) => void;
    onWordlistsUpdated: () => void;
    onClose: () => void;
}

export function useUploadWorkflow(options: UseUploadWorkflowOptions) {
    const { modelValue, wordlistId, onUploaded, onWordlistsUpdated, onClose } = options;

    const { isGenerating: slugGenerating, generateSlugWithFallback } = useSlugGeneration();

    // Step/mode state
    const uploadStep = ref<UploadStep>('dropzone');
    const uploadMode = ref<UploadMode>('new');
    const candidateState = ref<Record<string, 'pending' | 'accepted' | 'ignored'>>({});

    // Form state
    const selectedWordlistId = ref(wordlistId.value || '');
    const newWordlistName = ref('');
    const newWordlistDescription = ref('');
    const isSlugGenerated = ref(false);

    // Sub-composables
    const fileParser = useWordlistFileParser({
        onError: (message) => {
            upload.error.value = message;
        },
    });

    const upload = useWordlistUpload({
        onComplete: (words) => onUploaded(words),
        onWordlistsUpdated: () => onWordlistsUpdated(),
        onClose: () => onClose(),
    });

    const {
        reconcile,
        candidates: backendCandidates,
        isLoading: isLoadingReconcile,
    } = useWordlistReconcilePreview();

    // Computed
    const selectedWordlist = computed(() =>
        upload.wordlists.value.find((w) => w.id === selectedWordlistId.value),
    );

    const reviewCandidates = computed(() =>
        backendCandidates.value.map((candidate) => ({
            ...candidate,
            status: candidateState.value[candidate.id] ?? 'pending',
        })),
    );

    const totalOccurrences = computed(() =>
        fileParser.parsedWords.value.reduce((sum, word) => sum + (word.frequency || 1), 0),
    );

    const canUpload = computed(
        () =>
            fileParser.parsedWords.value.length > 0 &&
            (uploadMode.value === 'existing' ? !!selectedWordlistId.value : true),
    );

    // Helpers
    function normalizeKey(text: string) {
        return text.trim().toLowerCase();
    }

    function mergeResolvedWord(sourceText: string, resolvedText: string) {
        const source = normalizeKey(sourceText);
        const map = new Map<string, ParsedWord>();

        for (const word of fileParser.parsedWords.value) {
            const candidateText =
                normalizeKey(word.text) === source
                    ? resolvedText
                    : (word.resolvedText || word.text);
            const key = normalizeKey(candidateText);
            const existing = map.get(key);
            const nextWord: ParsedWord = {
                ...word,
                text: candidateText,
                resolvedText: candidateText,
            };
            if (existing) {
                existing.frequency += nextWord.frequency;
                if (nextWord.notes && !existing.notes) existing.notes = nextWord.notes;
            } else {
                map.set(key, nextWord);
            }
        }

        fileParser.parsedWords.value = Array.from(map.values()).sort(
            (a, b) => b.frequency - a.frequency,
        );
    }

    function acceptCandidate(candidate: ReviewCandidate) {
        candidateState.value[candidate.id] = 'accepted';
        mergeResolvedWord(candidate.sourceText, candidate.suggestedText);
    }

    function acceptCandidateById(candidateId: string) {
        const candidate = reviewCandidates.value.find((item) => item.id === candidateId);
        if (candidate) acceptCandidate(candidate);
    }

    function ignoreCandidate(candidate: ReviewCandidate) {
        candidateState.value[candidate.id] = 'ignored';
    }

    function ignoreCandidateById(candidateId: string) {
        const candidate = reviewCandidates.value.find((item) => item.id === candidateId);
        if (candidate) ignoreCandidate(candidate);
    }

    function markAllForReview() {
        for (const candidate of reviewCandidates.value) {
            candidateState.value[candidate.id] = 'pending';
        }
    }

    function reconcileAll() {
        const candidates = [...reviewCandidates.value];
        for (const candidate of candidates) {
            acceptCandidate(candidate);
        }
    }

    function ignoreAll() {
        for (const candidate of reviewCandidates.value) {
            ignoreCandidate(candidate);
        }
    }

    // Actions
    const handleAddFiles = async (files: File[]) => {
        upload.error.value = '';
        await fileParser.addFiles(files);
        if (fileParser.parsedWords.value.length > 0) {
            uploadStep.value = 'review';
            await reconcile(
                fileParser.parsedWords.value,
                uploadMode.value === 'existing' ? selectedWordlistId.value : undefined,
            );
        }
    };

    const onModalDrop = async (event: DragEvent) => {
        event.preventDefault();
        const files = Array.from(event.dataTransfer?.files || []);
        if (files.length > 0) {
            await handleAddFiles(files);
        }
    };

    const resetState = () => {
        fileParser.reset();
        upload.resetUploadState();
        selectedWordlistId.value = wordlistId.value || '';
        uploadMode.value = 'new';
        newWordlistName.value = '';
        newWordlistDescription.value = '';
        isSlugGenerated.value = false;
        uploadStep.value = 'dropzone';
        candidateState.value = {};
        backendCandidates.value = [];
    };

    const generateSlugName = async () => {
        const slugName = await generateSlugWithFallback();
        if (slugName) {
            newWordlistName.value = slugName;
            isSlugGenerated.value = true;
        }
    };

    const handleNameInput = () => {
        if (isSlugGenerated.value) {
            isSlugGenerated.value = false;
        }
    };

    const handleUpload = async () => {
        if (!canUpload.value) return;
        await upload.handleUpload(
            fileParser.parsedWords.value,
            uploadMode.value,
            selectedWordlistId.value,
            newWordlistName.value,
            newWordlistDescription.value,
        );
    };

    // Watches
    watch(
        () => modelValue.value,
        async (isOpen, wasOpen) => {
            if (isOpen) {
                if (upload.wordlists.value.length === 0) {
                    await upload.loadWordlists();
                }
                if (uploadMode.value === 'new' && !newWordlistName.value.trim()) {
                    await generateSlugName();
                }
            } else if (!isOpen && wasOpen) {
                setTimeout(() => {
                    resetState();
                }, 250);
            }
        },
    );

    watch(
        () => wordlistId.value,
        (newId) => {
            selectedWordlistId.value = newId || '';
        },
    );

    watch(
        () => fileParser.parsedWords.value.length,
        (count) => {
            if (count > 0) {
                uploadStep.value = 'review';
            } else if (!upload.isUploading.value) {
                uploadStep.value = 'dropzone';
            }
        },
    );

    watch(
        () => uploadMode.value,
        async (mode) => {
            if (mode === 'new' && !newWordlistName.value.trim()) {
                await generateSlugName();
            }
        },
    );

    onMounted(async () => {
        if (modelValue.value) {
            await upload.loadWordlists();
        }
    });

    return {
        // Step/mode
        uploadStep,
        uploadMode,

        // Form state
        selectedWordlistId,
        newWordlistName,
        newWordlistDescription,
        isSlugGenerated,
        slugGenerating,

        // Sub-composable passthrough
        fileParser,
        upload,
        isLoadingReconcile,

        // Computed
        selectedWordlist,
        reviewCandidates,
        totalOccurrences,
        canUpload,

        // Candidate actions
        acceptCandidateById,
        ignoreCandidateById,
        markAllForReview,
        reconcileAll,
        ignoreAll,

        // File/upload actions
        handleAddFiles,
        onModalDrop,
        generateSlugName,
        handleNameInput,
        handleUpload,
    };
}
