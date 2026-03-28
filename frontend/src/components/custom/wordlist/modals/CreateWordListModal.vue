<template>
    <Modal
        v-model="modelValue"
        :close-on-backdrop="!formState.isCreating.value"
        max-width="md"
        max-height="viewport"
    >
        <div class="mx-auto w-full max-w-md space-y-6">
            <!-- Header -->
            <div class="flex items-center justify-between">
                <h2 class="text-xl font-semibold">Create Wordlist</h2>
                <Button
                    @click="formState.closeModal"
                    variant="ghost"
                    size="sm"
                    class="h-6 w-6 p-0"
                >
                    <X class="h-4 w-4" />
                </Button>
            </div>

            <!-- Form -->
            <div class="space-y-4">
                <!-- Name with Slug Generation -->
                <div class="space-y-2">
                    <label class="text-sm font-medium">
                        Name <span class="text-destructive">*</span>
                    </label>
                    <div class="relative">
                        <Input
                            v-model="formState.form.value.name"
                            placeholder="e.g., SAT Vocabulary, Business Terms..."
                            class="w-full pr-10"
                            :class="{ 'border-destructive': formState.errors.value.name }"
                            @input="formState.handleNameInput"
                        />
                        <div class="absolute top-1/2 right-2 -translate-y-1/2">
                            <RefreshButton
                                :loading="formState.slugGenerating.value"
                                :disabled="formState.isCreating.value"
                                variant="ghost"
                                title="Generate random name"
                                @click="formState.generateSlugName"
                            />
                        </div>
                    </div>
                    <div class="flex items-center justify-between">
                        <p v-if="formState.errors.value.name" class="text-xs text-destructive">
                            {{ formState.errors.value.name }}
                        </p>
                        <p
                            v-else-if="formState.isSlugGenerated.value"
                            class="text-xs text-muted-foreground"
                        >
                            Random name generated - you can edit it or generate
                            a new one
                        </p>
                        <span v-else />
                        <span
                            class="text-xs"
                            :class="
                                formState.form.value.name.trim().length > 100
                                    ? 'text-destructive'
                                    : 'text-muted-foreground'
                            "
                        >
                            {{ formState.form.value.name.trim().length }}/100
                        </span>
                    </div>
                </div>

                <!-- Description -->
                <div class="space-y-2">
                    <label class="text-sm font-medium">Description</label>
                    <textarea
                        v-model="formState.form.value.description"
                        placeholder="Brief description of this wordlist..."
                        class="w-full resize-none rounded-md border border-border bg-background px-3 py-2 focus-visible:border-transparent focus-visible:ring-2 focus-visible:ring-primary"
                        rows="3"
                    />
                </div>

                <!-- Initial Words -->
                <div class="space-y-2">
                    <label class="text-sm font-medium"
                        >Initial Words (Optional)</label
                    >
                    <textarea
                        v-model="formState.initialWordsText.value"
                        placeholder="words"
                        class="w-full resize-none rounded-md border border-border bg-background px-3 py-2 focus-visible:border-transparent focus-visible:ring-2 focus-visible:ring-primary"
                        rows="4"
                    />
                    <p class="text-xs text-muted-foreground">
                        You can add more words later through the upload feature.
                    </p>
                </div>

                <!-- Tags -->
                <div class="space-y-2">
                    <label class="text-sm font-medium">Tags</label>
                    <div class="space-y-2">
                        <Input
                            v-model="formState.newTag.value"
                            placeholder="Add a tag..."
                            class="w-full"
                            :class="{ 'border-destructive': formState.errors.value.tag }"
                            @keydown.enter.prevent="formState.addTag"
                        />
                        <p v-if="formState.errors.value.tag" class="text-xs text-destructive">
                            {{ formState.errors.value.tag }}
                        </p>
                        <div
                            v-if="formState.form.value.tags.length > 0"
                            class="flex flex-wrap gap-1"
                        >
                            <span
                                v-for="tag in formState.form.value.tags"
                                :key="tag"
                                class="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-xs"
                            >
                                {{ tag }}
                                <button
                                    @click="formState.removeTag(tag)"
                                    class="hover:text-destructive"
                                >
                                    <X class="h-3 w-3" />
                                </button>
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Word Preview -->
                <div v-if="formState.parsedWords.value.length > 0" class="space-y-2">
                    <div class="flex items-center justify-between">
                        <label class="text-sm font-medium">
                            Words to Add ({{ formState.parsedWords.value.length }})
                        </label>
                        <Button
                            @click="formState.showAllWords.value = !formState.showAllWords.value"
                            variant="ghost"
                            size="sm"
                        >
                            {{ formState.showAllWords.value ? 'Show Less' : 'Show All' }}
                        </Button>
                    </div>

                    <div
                        class="max-h-32 overflow-y-auto rounded-md bg-muted/30 p-3"
                    >
                        <div class="grid grid-cols-2 gap-1">
                            <span
                                v-for="word in formState.displayedWords.value"
                                :key="word"
                                class="rounded bg-background px-2 py-1 text-sm"
                            >
                                {{ word }}
                            </span>
                        </div>

                        <div
                            v-if="!formState.showAllWords.value && formState.parsedWords.value.length > 10"
                            class="pt-2 text-center"
                        >
                            <span class="text-xs text-muted-foreground">
                                ... and {{ formState.parsedWords.value.length - 10 }} more
                            </span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Error Display -->
            <div
                v-if="formState.error.value"
                class="rounded-md border border-destructive/20 bg-destructive/10 p-3"
            >
                <p class="text-sm text-destructive">{{ formState.error.value }}</p>
            </div>

            <!-- Loading State -->
            <div v-if="formState.isCreating.value" class="space-y-2">
                <div class="flex items-center gap-2">
                    <div
                        class="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent"
                    ></div>
                    <span class="text-sm">Creating wordlist...</span>
                </div>
            </div>

            <!-- Actions -->
            <div class="flex justify-end gap-2 border-t pt-4">
                <Button
                    variant="outline"
                    @click="formState.closeModal"
                    :disabled="formState.isCreating.value"
                >
                    Cancel
                </Button>
                <Button
                    @click="formState.handleCreate"
                    :disabled="!formState.canCreate.value || formState.isCreating.value"
                    class="min-w-[100px]"
                >
                    <span v-if="formState.isCreating.value">Creating...</span>
                    <span v-else>Create Wordlist</span>
                </Button>
            </div>
        </div>
    </Modal>
</template>

<script setup lang="ts">
import { computed, toRef } from 'vue';
import { X } from 'lucide-vue-next';
import { Modal } from '@/components/custom';
import { Button, Input } from '@mkbabb/glass-ui';
import RefreshButton from '@/components/custom/common/RefreshButton.vue';
import type { WordList } from '@/types';
import { useWordListForm } from './composables/useWordListForm';

interface Props {
    modelValue: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    'update:modelValue': [value: boolean];
    created: [wordlist: WordList];
}>();

const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

const formState = useWordListForm({
    modelValue: toRef(props, 'modelValue'),
    onCreated: (wordlist) => emit('created', wordlist),
    onClose: () => {
        modelValue.value = false;
    },
});
</script>

<style scoped>
/* Custom styles for the create form */
textarea {
    resize: vertical;
    min-height: 80px;
}
</style>
