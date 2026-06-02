<template>
    <Modal v-model="modelValue" :close-on-backdrop="false">
        <div class="mx-auto w-full max-w-md space-y-6">
            <!-- Header -->
            <div class="flex items-center justify-between">
                <h2 class="text-xl font-semibold">
                    Add "{{ word }}" to Wordlist
                </h2>
                <Button
                    @click="closeModal"
                    variant="ghost"
                    size="sm"
                    class="h-6 w-6 p-0"
                >
                    <X class="h-4 w-4" />
                </Button>
            </div>

            <!-- Loading State -->
            <div v-if="isLoading" class="flex items-center justify-center py-8">
                <Loader2 class="h-6 w-6 animate-spin text-muted-foreground" />
            </div>

            <!-- Content -->
            <div v-else class="space-y-4">
                <!-- Create New Wordlist Option -->
                <div
                    class="card-surface interactive-item flex items-center justify-between p-3"
                >
                    <div class="flex items-center gap-3">
                        <Plus class="h-5 w-5 text-primary" />
                        <span class="font-medium">Create New Wordlist</span>
                    </div>
                    <Button
                        @click="showCreateModal = true"
                        variant="outline"
                        size="sm"
                    >
                        Create
                    </Button>
                </div>

                <!-- Existing Wordlists -->
                <div v-if="wordlists.length > 0" class="space-y-2">
                    <h3 class="text-sm font-medium text-muted-foreground">
                        Your Wordlists
                    </h3>
                    <div class="max-h-64 space-y-2 overflow-y-auto">
                        <div
                            v-for="wordlist in wordlists"
                            :key="wordlist.id"
                            class="card-surface interactive-item flex items-center justify-between p-3"
                        >
                            <div class="min-w-0 flex-1">
                                <div class="flex items-center gap-2">
                                    <span class="truncate font-medium">{{
                                        wordlist.name
                                    }}</span>
                                    <span
                                        v-if="isWordInWordlist(wordlist)"
                                        class="inline-flex items-center rounded-full border border-primary/20 bg-primary/10 px-2 py-0.5 text-xs text-primary"
                                    >
                                        Added {{ getWordFrequency(wordlist) }}x
                                    </span>
                                </div>
                                <div class="mt-1 text-xs text-muted-foreground">
                                    {{ wordlist.unique_words }} words
                                </div>
                            </div>
                            <Button
                                @click="addToWordlist(wordlist)"
                                :variant="
                                    isWordInWordlist(wordlist)
                                        ? 'outline'
                                        : 'default'
                                "
                                size="sm"
                                :disabled="isAdding"
                            >
                                <Loader2
                                    v-if="isAdding"
                                    class="mr-2 h-3 w-3 animate-spin"
                                />
                                {{
                                    isWordInWordlist(wordlist)
                                        ? 'Add Again'
                                        : 'Add'
                                }}
                            </Button>
                        </div>
                    </div>
                </div>

                <!-- Empty State -->
                <div v-else class="py-8 text-center">
                    <FileText
                        class="mx-auto mb-3 h-12 w-12 text-muted-foreground/50"
                    />
                    <p class="text-muted-foreground">No wordlists found</p>
                    <p class="mt-1 text-xs text-muted-foreground/70">
                        Create your first wordlist to get started
                    </p>
                </div>
            </div>

            <!-- Create Wordlist Modal -->
            <CreateWordListModal
                v-model="showCreateModal"
                :initial-words="[word]"
                @created="handleWordlistCreated"
            />
        </div>
    </Modal>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { X, Plus, FileText, Loader2 } from '@lucide/vue';
import { Button } from '@mkbabb/glass-ui/button';
import Modal from '@/components/custom/Modal.vue';
import CreateWordListModal from '../../wordlist/modals/CreateWordListModal.vue';
import type { WordList } from '@/types';
import { wordlistApi } from '@/api';
import { logger } from '@/utils/logger';

interface Props {
    modelValue: boolean;
    word: string;
}

const props = defineProps<Props>();
const emit = defineEmits<{
    'update:modelValue': [value: boolean];
    added: [wordlistName: string];
}>();

// Component state
const isLoading = ref(false);
const isAdding = ref(false);
const showCreateModal = ref(false);
const wordlists = ref<WordList[]>([]);

// Computed properties
const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

// Methods
const closeModal = () => {
    modelValue.value = false;
};

const loadWordlists = async () => {
    isLoading.value = true;
    try {
        const response = await wordlistApi.getWordlists({
            limit: 50,
        });

        // The /wordlists list endpoint returns metadata only — words are
        // loaded separately via /wordlists/{id}/words. We don't need to
        // know individual word membership here, so we leave that lookup
        // to the backend on add.
        wordlists.value = response.items.map((item: any) => ({
            ...item,
            id: item._id || item.id,
        }));
    } catch (error) {
        logger.error('Failed to load wordlists:', error);
    } finally {
        isLoading.value = false;
    }
};

// Word membership is no longer tracked client-side — the backend rejects
// duplicates/increments frequency on add. These stubs preserve the existing
// UI affordance shape without making per-list /words requests.
const isWordInWordlist = (_wordlist: WordList): boolean => false;
const getWordFrequency = (_wordlist: WordList): number => 0;

const addToWordlist = async (wordlist: WordList) => {
    isAdding.value = true;
    try {
        await wordlistApi.addWords(wordlist.id, [props.word]);

        // Bump local stats so the count in the list updates immediately;
        // membership state is fetched fresh on next open.
        const wordlistIndex = wordlists.value.findIndex(
            (w) => w.id === wordlist.id
        );
        if (wordlistIndex >= 0) {
            wordlists.value[wordlistIndex].unique_words++;
            wordlists.value[wordlistIndex].total_words++;
        }

        emit('added', wordlist.name);
    } catch (error) {
        logger.error('Failed to add word to wordlist:', error);
    } finally {
        isAdding.value = false;
    }
};

const handleWordlistCreated = (wordlist: WordList) => {
    wordlists.value.unshift(wordlist);
    showCreateModal.value = false;
    emit('added', wordlist.name);
};

// Watch for modal opening
watch(
    () => props.modelValue,
    (isOpen) => {
        if (isOpen) {
            loadWordlists();
        }
    }
);

// Load wordlists on mount if modal is already open
onMounted(() => {
    if (props.modelValue) {
        loadWordlists();
    }
});
</script>

<style scoped>
/* Additional styles if needed */
</style>
