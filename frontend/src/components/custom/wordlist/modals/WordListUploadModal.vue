<template>
    <Modal
        v-model="modelValue"
        :close-on-backdrop="!upload.isUploading.value"
        max-width="lg"
        max-height="viewport"
    >
        <div class="mx-auto w-full max-w-lg">
            <!-- Header -->
            <div class="mb-6 flex items-center justify-between">
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

            <!-- Main Content - scrolling handled by base Modal -->
            <div class="space-y-6">
                <!-- File Upload Area -->
                <UploadDropZone
                    :uploaded-files="fileParser.uploadedFiles.value"
                    @add-files="handleAddFiles"
                    @remove-file="fileParser.removeFile"
                />

                <!-- Parsed Words Preview -->
                <WordPreviewList :parsed-words="fileParser.parsedWords.value" />

                <!-- Wordlist Options -->
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

            <!-- Error Display -->
            <div
                v-if="upload.error.value"
                class="mt-4 rounded-md border border-destructive/20 bg-destructive/10 p-3"
            >
                <p class="text-sm text-destructive">{{ upload.error.value }}</p>
            </div>

            <!-- Loading State -->
            <div v-if="upload.isUploading.value" class="mt-6 space-y-4">
                <LoadingProgress
                    :progress="upload.uploadProgress.value"
                    :current-stage="upload.uploadStage.value"
                    :stage-definitions="upload.uploadStageDefinitions.value"
                    :category="upload.uploadCategory.value"
                    :show-details="true"
                />
            </div>

            <!-- Actions - Full width HR -->
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
                        <span v-if="upload.isUploading.value"
                            >Uploading...</span
                        >
                        <span v-else>Add Words</span>
                    </Button>
                </div>
            </div>
        </div>
    </Modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { X } from 'lucide-vue-next';
import { Modal } from '@/components/custom';
import { Button } from '@/components/ui/button';
import { LoadingProgress } from '@/components/custom/loading';
import { useSlugGeneration } from '@/composables/useSlugGeneration';
import UploadDropZone from '../UploadDropZone.vue';
import WordPreviewList from '../WordPreviewList.vue';
import WordlistTargetForm from '../WordlistTargetForm.vue';
import { useWordlistFileParser } from '../composables/useWordlistFileParser';
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

// Slug generation
const { isGenerating: slugGenerating, generateSlugWithFallback } =
    useSlugGeneration();

// Component state
const selectedWordlistId = ref(props.wordlistId || '');
const uploadMode = ref<'new' | 'existing'>('new');
const newWordlistName = ref('');
const newWordlistDescription = ref('');
const isSlugGenerated = ref(false);

// Computed properties
const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

const closeModal = () => {
    modelValue.value = false;
};

// File parser composable
const fileParser = useWordlistFileParser({
    onError: (message) => {
        upload.error.value = message;
    },
});

// Upload composable
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

const selectedWordlist = computed(() =>
    upload.wordlists.value.find((w) => w.id === selectedWordlistId.value)
);

const canUpload = computed(() => {
    return (
        fileParser.parsedWords.value.length > 0 &&
        (uploadMode.value === 'existing' ? selectedWordlistId.value : true)
    );
});

// Methods
const handleAddFiles = async (files: File[]) => {
    upload.error.value = '';
    await fileParser.addFiles(files);
};

const resetState = () => {
    fileParser.reset();
    upload.resetUploadState();
    selectedWordlistId.value = props.wordlistId || '';
    uploadMode.value = 'new';
    newWordlistName.value = '';
    newWordlistDescription.value = '';
    isSlugGenerated.value = false;
};

// Slug generation methods
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

// Track if we've already generated on modal open to prevent duplicates
const hasGeneratedOnOpen = ref(false);

// Load wordlists when modal opens, reset when modal closes
watch(
    () => props.modelValue,
    async (isOpen, wasOpen) => {
        if (isOpen) {
            hasGeneratedOnOpen.value = false;
            if (upload.wordlists.value.length === 0) {
                await upload.loadWordlists();
            }
            if (uploadMode.value === 'new' && !newWordlistName.value.trim()) {
                await generateSlugName();
                hasGeneratedOnOpen.value = true;
            }
        } else if (!isOpen && wasOpen) {
            setTimeout(() => {
                resetState();
            }, 250);
        }
    }
);

// Auto-generate slug when switching to "new" mode and name is empty
watch(
    () => uploadMode.value,
    async (mode) => {
        if (
            mode === 'new' &&
            !newWordlistName.value.trim() &&
            !hasGeneratedOnOpen.value
        ) {
            await generateSlugName();
        }
    }
);

// Watch for prop changes
watch(
    () => props.wordlistId,
    (newId) => {
        selectedWordlistId.value = newId || '';
    }
);

// Load wordlists on mount
onMounted(async () => {
    if (props.modelValue) {
        await upload.loadWordlists();
    }
});
</script>

<style scoped>
/* Custom styles for drag and drop */
</style>
