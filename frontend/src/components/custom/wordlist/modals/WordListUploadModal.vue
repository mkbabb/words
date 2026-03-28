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
                    <div class="rounded-2xl glass-subtle p-4">
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
import { computed, toRef } from 'vue';
import { ChevronLeft, X } from 'lucide-vue-next';
import { Modal } from '@/components/custom';
import { Button } from '@mkbabb/glass-ui';
import { LoadingProgress } from '@/components/custom/loading';
import UploadDropZone from '../UploadDropZone.vue';
import WordPreviewList from '../cards/WordPreviewList.vue';
import WordlistTargetForm from '../WordlistTargetForm.vue';
import { useUploadWorkflow } from './composables/useUploadWorkflow';

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

const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

const closeModal = () => {
    modelValue.value = false;
};

const workflow = useUploadWorkflow({
    modelValue,
    wordlistId: toRef(props, 'wordlistId'),
    onUploaded: (words) => emit('uploaded', words),
    onWordlistsUpdated: () => emit('wordlists-updated'),
    onClose: () => closeModal(),
});

const {
    uploadStep,
    uploadMode,
    selectedWordlistId,
    newWordlistName,
    newWordlistDescription,
    isSlugGenerated,
    slugGenerating,
    fileParser,
    upload,
    isLoadingReconcile,
    selectedWordlist,
    reviewCandidates,
    totalOccurrences,
    canUpload,
    acceptCandidateById,
    ignoreCandidateById,
    markAllForReview,
    reconcileAll,
    ignoreAll,
    handleAddFiles,
    onModalDrop,
    generateSlugName,
    handleNameInput,
    handleUpload,
} = workflow;
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
