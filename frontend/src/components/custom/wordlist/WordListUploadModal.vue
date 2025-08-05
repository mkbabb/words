<template>
    <Modal v-model="modelValue" :close-on-backdrop="!isUploading" max-width="lg" max-height="viewport">
        <div class="w-full max-w-lg mx-auto">
            <!-- Header -->
            <div class="flex items-center justify-between mb-6">
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
                    <div class="space-y-4">
                        <div
                            @drop="onDrop"
                            @dragover.prevent
                            @dragenter.prevent
                            :class="[
                                'cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition-colors',
                                isDragging
                                    ? 'border-primary bg-primary/5'
                                    : 'border-muted-foreground/25 hover:border-muted-foreground/50',
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
                                <Upload
                                    class="mx-auto h-8 w-8
                                        text-muted-foreground"
                                />
                                <div>
                                    <p class="font-medium">
                                        Drop files here or click to browse
                                    </p>
                                    <p class="text-sm text-muted-foreground">
                                        Supports .txt, .csv, and .json files
                                    </p>
                                </div>
                            </div>
                        </div>

                        <!-- File Format Instructions -->
                        <div class="space-y-1 text-xs text-muted-foreground">
                            <p><strong>Supported formats:</strong></p>
                            <ul class="ml-2 list-inside list-disc space-y-0.5">
                                <li>
                                    <strong>.txt:</strong> One word per line
                                </li>
                                <li>
                                    <strong>.csv:</strong> word,frequency,notes
                                    (headers optional)
                                </li>
                                <li>
                                    <strong>.json:</strong> Array of words or
                                    word objects
                                </li>
                            </ul>
                        </div>
                    </div>

                    <!-- File Preview -->
                    <div v-if="uploadedFiles.length > 0" class="space-y-3">
                        <h3 class="font-medium">Uploaded Files</h3>
                        <div class="max-h-32 space-y-2 overflow-y-auto">
                            <div
                                v-for="file in uploadedFiles"
                                :key="file.name"
                                class="flex items-center justify-between
                                    rounded-md bg-muted/50 p-2"
                            >
                                <div class="flex items-center gap-2">
                                    <FileText class="h-4 w-4" />
                                    <span class="text-sm">{{ file.name }}</span>
                                </div>
                                <Button
                                    @click="removeFile(file)"
                                    variant="ghost"
                                    size="sm"
                                    class="h-6 w-6 p-0"
                                >
                                    <X class="h-3 w-3" />
                                </Button>
                            </div>
                        </div>
                    </div>

                    <!-- Parsed Words Preview -->
                    <div v-if="parsedWords.length > 0" class="space-y-3">
                        <div class="flex items-center justify-between">
                            <h3 class="font-medium">
                                Words Found ({{ parsedWords.length }})
                            </h3>
                            <Button
                                @click="showAllWords = !showAllWords"
                                variant="ghost"
                                size="sm"
                            >
                                {{ showAllWords ? 'Show Less' : 'Show All' }}
                            </Button>
                        </div>

                        <div
                            class="max-h-40 overflow-y-auto rounded-md
                                bg-muted/30 p-3"
                        >
                            <div class="grid grid-cols-1 gap-1">
                                <div
                                    v-for="(word, index) in displayedWords"
                                    :key="index"
                                    class="flex items-center justify-between
                                        py-1"
                                >
                                    <span class="text-sm">{{ word.text }}</span>
                                    <div
                                        class="flex items-center gap-2 text-xs
                                            text-muted-foreground"
                                    >
                                        <span v-if="word.frequency > 1"
                                            >{{ word.frequency }}x</span
                                        >
                                        <span
                                            v-if="word.notes"
                                            class="rounded bg-muted px-1"
                                        >
                                            {{ word.notes }}
                                        </span>
                                    </div>
                                </div>
                            </div>

                            <div
                                v-if="!showAllWords && parsedWords.length > 10"
                                class="pt-2 text-center"
                            >
                                <span class="text-xs text-muted-foreground">
                                    ... and {{ parsedWords.length - 10 }} more
                                </span>
                            </div>
                        </div>
                    </div>

                    <!-- Wordlist Options -->
                    <div v-if="parsedWords.length > 0" class="space-y-4">
                        <!-- Upload Mode Toggle -->
                        <div class="space-y-2">
                            <label class="text-sm font-medium"
                                >Upload Mode</label
                            >
                            <div class="flex rounded-lg border bg-muted/30 p-1">
                                <Button
                                    @click="uploadMode = 'new'"
                                    :variant="
                                        uploadMode === 'new'
                                            ? 'default'
                                            : 'ghost'
                                    "
                                    size="sm"
                                    class="flex-1 text-sm"
                                >
                                    Create New
                                </Button>
                                <Button
                                    @click="uploadMode = 'existing'"
                                    :variant="
                                        uploadMode === 'existing'
                                            ? 'default'
                                            : 'ghost'
                                    "
                                    size="sm"
                                    class="flex-1 text-sm"
                                >
                                    Add to Existing
                                </Button>
                            </div>
                        </div>

                        <!-- Existing Wordlist Selection -->
                        <div v-if="uploadMode === 'existing'" class="space-y-2">
                            <label class="text-sm font-medium"
                                >Select Wordlist</label
                            >
                            <DropdownMenu>
                                <DropdownMenuTrigger as-child>
                                    <Button
                                        variant="outline"
                                        class="w-full justify-between"
                                        :disabled="isLoadingWordlist"
                                    >
                                        <span>
                                            {{
                                                selectedWordlist
                                                    ? `${selectedWordlist.name} (${selectedWordlist.unique_words} words)`
                                                    : 'Select a wordlist...'
                                            }}
                                        </span>
                                        <ChevronDown
                                            class="h-4 w-4 opacity-50"
                                        />
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent class="w-full">
                                    <DropdownMenuItem
                                        v-for="wordlist in wordlists"
                                        :key="wordlist.id"
                                        @click="
                                            selectedWordlistId = wordlist.id
                                        "
                                        class="cursor-pointer"
                                    >
                                        <div class="flex flex-col items-start">
                                            <span class="font-medium">{{
                                                wordlist.name
                                            }}</span>
                                            <span
                                                class="text-xs
                                                    text-muted-foreground"
                                                >{{
                                                    wordlist.unique_words
                                                }}
                                                words</span
                                            >
                                        </div>
                                    </DropdownMenuItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>

                        <!-- New Wordlist Form -->
                        <div v-if="uploadMode === 'new'" class="space-y-3">
                            <!-- Name with Slug Generation -->
                            <div class="space-y-2">
                                <label class="text-sm font-medium">Name</label>
                                <div class="relative">
                                    <Input
                                        v-model="newWordlistName"
                                        placeholder="Wordlist name (optional)..."
                                        class="w-full pr-10"
                                        @input="handleNameInput"
                                    />
                                    <div class="absolute right-2 top-1/2 -translate-y-1/2">
                                        <RefreshButton
                                            :loading="slugGenerating"
                                            :disabled="isUploading"
                                            variant="ghost"
                                            title="Generate random name"
                                            @click="generateSlugName"
                                        />
                                    </div>
                                </div>
                                <p v-if="isSlugGenerated" class="text-xs text-muted-foreground">Random name generated - you can edit it or generate a new one</p>
                            </div>
                            <!-- Description -->
                            <div class="space-y-2">
                                <label class="text-sm font-medium">Description</label>
                                <Input
                                    v-model="newWordlistDescription"
                                    placeholder="Description (optional)..."
                                    class="w-full"
                                />
                            </div>
                        </div>
                    </div>
            </div>

            <!-- Error Display -->
            <div
                v-if="error"
                class="mt-4 rounded-md border border-destructive/20
                    bg-destructive/10 p-3"
            >
                <p class="text-sm text-destructive">{{ error }}</p>
            </div>

            <!-- Loading State -->
            <div v-if="isUploading" class="mt-6 space-y-4">
                <LoadingProgress
                    :progress="uploadProgress"
                    :current-stage="uploadStage"
                    :stage-definitions="uploadStageDefinitions"
                    :category="uploadCategory"
                    :show-details="true"
                />
            </div>

            <!-- Actions - Full width HR -->
            <div class="mt-6 pt-4 border-t border-border/20">
                <div class="flex justify-end gap-2">
                    <Button
                        variant="outline"
                        @click="closeModal"
                        :disabled="isUploading"
                    >
                        Cancel
                    </Button>
                    <Button
                        @click="handleUpload"
                        :disabled="!canUpload || isUploading"
                        class="min-w-[100px]"
                    >
                        <span v-if="isUploading">Uploading...</span>
                        <span v-else>Add Words</span>
                    </Button>
                </div>
            </div>
        </div>
    </Modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { Upload, X, FileText, ChevronDown } from 'lucide-vue-next';
import { Modal } from '@/components/custom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { LoadingProgress } from '@/components/custom/loading';
import RefreshButton from '@/components/custom/common/RefreshButton.vue';
import { useToast } from '@/components/ui/toast/use-toast';
import { useSlugGeneration } from '@/composables/useSlugGeneration';
import { wordlistApi } from '@/api';
import type { WordList } from '@/types';

interface Props {
    modelValue: boolean;
    wordlistId?: string;
}

interface ParsedWord {
    text: string;
    frequency: number;
    notes?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    'update:modelValue': [value: boolean];
    uploaded: [words: string[]];
    'wordlists-updated': [];
}>();

// Slug generation
const { isGenerating: slugGenerating, generateSlugWithFallback } = useSlugGeneration();

// Component state
const fileInput = ref<HTMLInputElement>();
const uploadedFiles = ref<File[]>([]);
const parsedWords = ref<ParsedWord[]>([]);
const selectedWordlistId = ref(props.wordlistId || '');
const uploadMode = ref<'new' | 'existing'>('new');
const newWordlistName = ref('');
const newWordlistDescription = ref('');
const showAllWords = ref(false);
const isDragging = ref(false);
const isUploading = ref(false);
const isSlugGenerated = ref(false);
const uploadProgress = ref(0);
const uploadStatus = ref('');
const uploadStage = ref('');
const uploadStageDefinitions = ref<
    Array<{ progress: number; label: string; description: string }>
>([]);
const uploadCategory = ref('');
const error = ref('');

// Toast notifications
const { toast } = useToast();

// Wordlist state
const wordlists = ref<WordList[]>([]);
const isLoadingWordlist = ref(false);

// Load wordlists function
const loadWordlists = async () => {
  try {
    isLoadingWordlist.value = true;
    const response = await wordlistApi.getWordlists();
    wordlists.value = response.items;
    return response.items;
  } catch (error) {
    console.error('Failed to load wordlists:', error);
    toast({
      title: "Error",
      description: "Failed to load wordlists",
      variant: "destructive",
    });
    return [];
  } finally {
    isLoadingWordlist.value = false;
  }
};
const selectedWordlist = computed(() =>
    wordlists.value.find((w) => w.id === selectedWordlistId.value)
);

// Computed properties
const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

const displayedWords = computed(() => {
    return showAllWords.value
        ? parsedWords.value
        : parsedWords.value.slice(0, 10);
});

const canUpload = computed(() => {
    return (
        parsedWords.value.length > 0 &&
        (uploadMode.value === 'existing' ? selectedWordlistId.value : true)
    ); // Name is optional for new wordlists
});

// Methods
const closeModal = () => {
    modelValue.value = false;
    // State reset handled by modelValue watcher
};

const resetState = () => {
    uploadedFiles.value = [];
    parsedWords.value = [];
    selectedWordlistId.value = props.wordlistId || '';
    uploadMode.value = 'new';
    newWordlistName.value = '';
    newWordlistDescription.value = '';
    showAllWords.value = false;
    error.value = '';
    uploadProgress.value = 0;
    uploadStatus.value = '';
    uploadStage.value = '';
    uploadStageDefinitions.value = [];
    uploadCategory.value = '';
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
    // Clear the slug generated flag when user manually types
    if (isSlugGenerated.value) {
        isSlugGenerated.value = false;
    }
};

const onDrop = (event: DragEvent) => {
    event.preventDefault();
    isDragging.value = false;

    const files = Array.from(event.dataTransfer?.files || []);
    addFiles(files);
};

const onFileChange = (event: Event) => {
    const target = event.target as HTMLInputElement;
    const files = Array.from(target.files || []);
    addFiles(files);
};

const addFiles = async (files: File[]) => {
    error.value = '';

    for (const file of files) {
        if (file.size > 10 * 1024 * 1024) {
            // 10MB limit
            error.value = `File ${file.name} is too large (max 10MB)`;
            continue;
        }

        if (!file.name.match(/\.(txt|csv|json)$/i)) {
            error.value = `File ${file.name} has unsupported format`;
            continue;
        }

        uploadedFiles.value.push(file);
        await parseFile(file);
    }
};

const parseFile = async (file: File): Promise<void> => {
    try {
        const text = await file.text();
        const extension = file.name.toLowerCase().split('.').pop();

        let newWords: ParsedWord[] = [];

        switch (extension) {
            case 'txt':
                newWords = parseTxtFile(text);
                break;
            case 'csv':
                newWords = parseCsvFile(text);
                break;
            case 'json':
                newWords = parseJsonFile(text);
                break;
        }

        // Merge with existing parsed words, combining frequencies
        const wordMap = new Map<string, ParsedWord>();

        // Add existing words
        parsedWords.value.forEach((word) => {
            wordMap.set(word.text.toLowerCase(), word);
        });

        // Add new words
        newWords.forEach((word) => {
            const key = word.text.toLowerCase();
            if (wordMap.has(key)) {
                const existing = wordMap.get(key)!;
                existing.frequency += word.frequency;
                if (word.notes && !existing.notes) {
                    existing.notes = word.notes;
                }
            } else {
                wordMap.set(key, word);
            }
        });

        parsedWords.value = Array.from(wordMap.values()).sort(
            (a, b) => b.frequency - a.frequency
        );
    } catch (err) {
        console.error('File parsing error:', err);
        error.value = `Failed to parse ${file.name}`;
    }
};

const parseTxtFile = (text: string): ParsedWord[] => {
    return text
        .split('\n')
        .map((line) => line.trim())
        .filter((line) => line && !line.startsWith('#'))
        .map((word) => ({ text: word, frequency: 1 }));
};

const parseCsvFile = (text: string): ParsedWord[] => {
    const lines = text.split('\n').filter((line) => line.trim());
    const hasHeaders = lines[0]?.toLowerCase().includes('word');
    const dataLines = hasHeaders ? lines.slice(1) : lines;

    return dataLines
        .map((line) => {
            const [word, frequency = '1', notes = ''] = line
                .split(',')
                .map((s) => s.trim());
            return {
                text: word,
                frequency: parseInt(frequency) || 1,
                notes: notes || undefined,
            };
        })
        .filter((item) => item.text);
};

const parseJsonFile = (text: string): ParsedWord[] => {
    const data = JSON.parse(text);

    if (Array.isArray(data)) {
        return data
            .map((item) => {
                if (typeof item === 'string') {
                    return { text: item, frequency: 1 };
                } else if (typeof item === 'object' && item.text) {
                    return {
                        text: item.text,
                        frequency: item.frequency || 1,
                        notes: item.notes,
                    };
                }
                return null;
            })
            .filter(Boolean) as ParsedWord[];
    }

    throw new Error('JSON must be an array');
};

const removeFile = (fileToRemove: File) => {
    uploadedFiles.value = uploadedFiles.value.filter(
        (file) => file !== fileToRemove
    );

    // Re-parse remaining files
    parsedWords.value = [];
    uploadedFiles.value.forEach((file) => parseFile(file));
};

const handleUpload = async () => {
    if (!canUpload.value) return;

    isUploading.value = true;
    uploadProgress.value = 0;
    uploadStatus.value = 'Preparing upload...';
    error.value = '';

    try {
        const words = parsedWords.value.map((w) => w.text);

        if (uploadMode.value === 'new') {
            // Create new wordlist with streaming
            uploadStatus.value = 'Creating new wordlist...';
            uploadStage.value = 'initializing';
            uploadCategory.value = 'wordlist_creation';

            // Create FormData for file upload
            const fileName = newWordlistName.value.trim() || 'wordlist';
            const blob = new Blob([words.join('\n')], { type: 'text/plain' });
            const file = new File([blob], `${fileName}.txt`, {
                type: 'text/plain',
            });

            const response = await wordlistApi.uploadWordlistStream(
                file,
                {
                    name: newWordlistName.value.trim() || undefined, // Let backend auto-generate if empty
                    description:
                        newWordlistDescription.value.trim() || undefined,
                },
                (stage, progress, message) => {
                    uploadStage.value = stage;
                    uploadProgress.value = progress;
                    uploadStatus.value = message || `${stage}...`;

                    // Check if this is completion via progress callback
                    if (stage === 'COMPLETE' || progress === 100) {
                        // Trigger close from progress callback as backup
                        setTimeout(async () => {
                            await loadWordlists();
                            emit('uploaded', words);
                            emit('wordlists-updated');
                            closeModal();
                        }, 500);
                    }
                },
                (category, stages) => {
                    uploadCategory.value = category;
                    uploadStageDefinitions.value = stages;
                }
            );

            if (response) {
                // Refresh wordlists and emit events
                await loadWordlists();
                emit('uploaded', words);
                emit('wordlists-updated');
            }
        } else {
            // Add to existing wordlist - TODO: implement streaming endpoint
            uploadStatus.value = 'Adding words to wordlist...';
            uploadProgress.value = 50;

            // Use the addWords API method
            await wordlistApi.addWords(selectedWordlistId.value, words);
            uploadProgress.value = 100;

            // Refresh wordlists and emit events
            await loadWordlists();
            emit('uploaded', words);
            emit('wordlists-updated');
        }

        // Close modal on completion
        uploadStatus.value = 'Complete!';
        closeModal();
    } catch (err) {
        console.error('Upload error:', err);
        error.value =
            err instanceof Error
                ? err.message
                : 'Failed to upload words. Please try again.';
    } finally {
        isUploading.value = false;
    }
};

// Track if we've already generated on modal open to prevent duplicates
const hasGeneratedOnOpen = ref(false);

// Load wordlists when modal opens, reset when modal closes
watch(
    () => props.modelValue,
    async (isOpen, wasOpen) => {
        if (isOpen) {
            hasGeneratedOnOpen.value = false; // Reset the flag
            if (wordlists.value.length === 0) {
                await loadWordlists();
            }
            // Auto-generate slug when modal opens in "new" mode and name is empty
            if (uploadMode.value === 'new' && !newWordlistName.value.trim()) {
                await generateSlugName();
                hasGeneratedOnOpen.value = true;
            }
        } else if (!isOpen && wasOpen) {
            // Modal is closing - reset state after animation completes (250ms from Modal.vue)
            setTimeout(() => {
                resetState();
            }, 250);
        }
    }
);

// Auto-generate slug when switching to "new" mode and name is empty
// Only if we haven't already generated on modal open
watch(() => uploadMode.value, async (mode) => {
    if (mode === 'new' && !newWordlistName.value.trim() && !hasGeneratedOnOpen.value) {
        await generateSlugName();
    }
});

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
        await loadWordlists();
    }
});
</script>

<style scoped>
/* Custom styles for drag and drop */
</style>
