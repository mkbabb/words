<template>
    <Modal
        v-model="modelValue"
        :close-on-backdrop="!upload.isUploading.value"
        max-width="lg"
        max-height="viewport"
    >
        <div
            class="mx-auto w-full max-w-4xl"
            @drop="onModalDrop"
            @dragover.prevent
            @dragenter.prevent
        >
            <div class="mb-6 flex items-center justify-between">
                <div class="flex items-center gap-2">
                    <Button
                        v-if="uploadStep === 'review'"
                        @click="uploadStep = 'dropzone'"
                        variant="ghost"
                        size="sm"
                        class="h-8 w-8 p-0"
                        title="Back to files"
                    >
                        <ChevronLeft class="h-4 w-4" />
                    </Button>
                    <div>
                        <h2 class="text-xl font-semibold">
                            {{ uploadStep === 'review' ? 'Review Parsed Words' : 'Upload Words' }}
                        </h2>
                        <p class="text-sm text-muted-foreground">
                            {{ uploadStep === 'review' ? 'Review the parsed output before committing it to a wordlist.' : 'Drop files anywhere in the modal to start.' }}
                        </p>
                    </div>
                </div>
                <Button
                    @click="closeModal"
                    variant="ghost"
                    size="sm"
                    class="h-6 w-6 p-0"
                >
                    <X class="h-4 w-4" />
                </Button>
            </div>

            <Transition name="upload-step" mode="out-in">
                <div
                    v-if="uploadStep === 'dropzone'"
                    key="dropzone"
                >
                    <UploadDropZone
                        :uploaded-files="fileParser.uploadedFiles.value"
                        @add-files="handleAddFiles"
                        @remove-file="fileParser.removeFile"
                    />
                </div>

                <div
                    v-else
                    key="review"
                    class="space-y-6"
                >
                    <div class="rounded-2xl glass-light p-4">
                        <div class="mb-4 flex items-center justify-between gap-3">
                            <div>
                                <p class="font-medium">Parsed output</p>
                                <p class="text-sm text-muted-foreground">
                                    {{ fileParser.parsedWords.value.length }} unique words, {{ totalOccurrences }} total occurrences
                                </p>
                            </div>
                            <Button
                                variant="ghost"
                                size="sm"
                                @click="uploadStep = 'dropzone'"
                            >
                                Back to files
                            </Button>
                        </div>

                        <WordPreviewList
                            :parsed-words="fileParser.parsedWords.value"
                            :review-candidates="reviewCandidates"
                            :is-loading-reconcile="isLoadingReconcile"
                            @review-all="markAllForReview"
                            @reconcile-all="reconcileAll"
                            @ignore-all="ignoreAll"
                            @accept-candidate="acceptCandidateById"
                            @ignore-candidate="ignoreCandidateById"
                        />
                    </div>

                    <WordlistTargetForm
                        :show-form="fileParser.parsedWords.value.length > 0"
                        :upload-mode="uploadMode"
                        @update:upload-mode="uploadMode = $event"
                        :wordlists="upload.wordlists.value"
                        :selected-wordlist="selectedWordlist"
                        :is-loading-wordlist="upload.isLoadingWordlist.value"
                        :new-wordlist-name="newWordlistName"
                        @update:new-wordlist-name="newWordlistName = $event"
                        :new-wordlist-description="newWordlistDescription"
                        @update:new-wordlist-description="
                            newWordlistDescription = $event
                        "
                        :slug-generating="slugGenerating"
                        :is-uploading="upload.isUploading.value"
                        :is-slug-generated="isSlugGenerated"
                        @update:selected-wordlist-id="selectedWordlistId = $event"
                        @name-input="handleNameInput"
                        @generate-slug="generateSlugName"
                    />
                </div>
            </Transition>

            <div
                v-if="upload.error.value"
                class="mt-4 rounded-md border border-destructive/20 bg-destructive/10 p-3"
            >
                <p class="text-sm text-destructive">{{ upload.error.value }}</p>
            </div>

            <div v-if="upload.isUploading.value" class="mt-6 space-y-4">
                <LoadingProgress
                    :progress="upload.uploadProgress.value"
                    :current-stage="upload.uploadStage.value"
                    :stage-definitions="upload.uploadStageDefinitions.value"
                    :category="upload.uploadCategory.value"
                    :show-details="true"
                />
            </div>

            <div class="mt-6 border-t border-border/20 pt-4">
                <div class="flex justify-end gap-2">
                    <Button
                        variant="outline"
                        @click="closeModal"
                        :disabled="upload.isUploading.value"
                    >
                        Cancel
                    </Button>
                    <Button
                        @click="handleUpload"
                        :disabled="!canUpload || upload.isUploading.value"
                        class="min-w-[100px]"
                    >
                        <span v-if="upload.isUploading.value">Uploading...</span>
                        <span v-else>Add Words</span>
                    </Button>
                </div>
            </div>
        </div>
    </Modal>
</template>

<script setup lang="ts">
import { computed, ref, watch, onMounted } from 'vue';
import { ChevronLeft, X } from 'lucide-vue-next';
import { Modal } from '@/components/custom';
import { Button } from '@/components/ui/button';
import { LoadingProgress } from '@/components/custom/loading';
import { useSlugGeneration } from '@/composables/useSlugGeneration';
import UploadDropZone from '../UploadDropZone.vue';
import WordPreviewList from '../cards/WordPreviewList.vue';
import WordlistTargetForm from '../WordlistTargetForm.vue';
import { useWordlistFileParser, type ParsedWord } from '../composables/useWordlistFileParser';
import { useWordlistReconcilePreview, type ReviewCandidate } from '../composables/useWordlistReconcilePreview';
import { useWordlistUpload } from '../composables/useWordlistUpload';

interface Props {
    modelValue: boolean;
    wordlistId?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    'update:modelValue': [value: boolean];
    uploaded: [words: string[]];
    'wordlists-updated': [];
}>();

const { isGenerating: slugGenerating, generateSlugWithFallback } =
    useSlugGeneration();

const selectedWordlistId = ref(props.wordlistId || '');
const uploadMode = ref<'new' | 'existing'>('new');
const newWordlistName = ref('');
const newWordlistDescription = ref('');
const isSlugGenerated = ref(false);
const uploadStep = ref<'dropzone' | 'review'>('dropzone');
const candidateState = ref<Record<string, 'pending' | 'accepted' | 'ignored'>>({});

const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

const closeModal = () => {
    modelValue.value = false;
};

const fileParser = useWordlistFileParser({
    onError: (message) => {
        upload.error.value = message;
    },
});

const upload = useWordlistUpload({
    onComplete: (words) => {
        emit('uploaded', words);
    },
    onWordlistsUpdated: () => {
        emit('wordlists-updated');
    },
    onClose: () => {
        closeModal();
    },
});

const { reconcile, candidates: backendCandidates, isLoading: isLoadingReconcile } = useWordlistReconcilePreview();

const selectedWordlist = computed(() =>
    upload.wordlists.value.find((w) => w.id === selectedWordlistId.value)
);

const reviewCandidates = computed(() => {
    return backendCandidates.value.map((candidate) => ({
        ...candidate,
        status: candidateState.value[candidate.id] ?? 'pending',
    }));
});

const totalOccurrences = computed(() =>
    fileParser.parsedWords.value.reduce((sum, word) => sum + (word.frequency || 1), 0)
);

const canUpload = computed(() => {
    return (
        fileParser.parsedWords.value.length > 0 &&
        (uploadMode.value === 'existing' ? selectedWordlistId.value : true)
    );
});

function normalizeKey(text: string) {
    return text.trim().toLowerCase();
}

function mergeResolvedWord(sourceText: string, resolvedText: string) {
    const source = normalizeKey(sourceText);
    const next: ParsedWord[] = [];
    const map = new Map<string, ParsedWord>();

    for (const word of fileParser.parsedWords.value) {
        const candidateText =
            normalizeKey(word.text) === source ? resolvedText : (word.resolvedText || word.text);
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

    next.push(...map.values());
    fileParser.parsedWords.value = next.sort((a, b) => b.frequency - a.frequency);
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

const handleAddFiles = async (files: File[]) => {
    upload.error.value = '';
    await fileParser.addFiles(files);
    if (fileParser.parsedWords.value.length > 0) {
        uploadStep.value = 'review';
        // Trigger backend reconcile preview
        await reconcile(
            fileParser.parsedWords.value,
            uploadMode.value === 'existing' ? selectedWordlistId.value : undefined,
        );
    }
};

/** Allow dropping files anywhere in the modal content area. */
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
    selectedWordlistId.value = props.wordlistId || '';
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
        newWordlistDescription.value
    );
};

watch(
    () => props.modelValue,
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
    }
);

watch(
    () => props.wordlistId,
    (newId) => {
        selectedWordlistId.value = newId || '';
    }
);

watch(
    () => fileParser.parsedWords.value.length,
    (count) => {
        if (count > 0) {
            uploadStep.value = 'review';
        } else if (!upload.isUploading.value) {
            uploadStep.value = 'dropzone';
        }
    }
);

watch(
    () => uploadMode.value,
    async (mode) => {
        if (mode === 'new' && !newWordlistName.value.trim()) {
            await generateSlugName();
        }
    }
);

onMounted(async () => {
    if (props.modelValue) {
        await upload.loadWordlists();
    }
});
</script>

<style scoped>
.upload-step-enter-active,
.upload-step-leave-active {
    transition:
        opacity 180ms var(--ease-apple-smooth),
        transform 220ms var(--ease-apple-spring);
}

.upload-step-enter-from,
.upload-step-leave-to {
    opacity: 0;
    transform: translateY(8px);
}
</style>
