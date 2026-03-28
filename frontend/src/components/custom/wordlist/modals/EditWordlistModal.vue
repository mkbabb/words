<template>
    <Modal
        v-model="modelValue"
        :close-on-backdrop="!isSaving"
        max-width="md"
        max-height="viewport"
    >
        <div class="mx-auto w-full max-w-md space-y-6">
            <!-- Header -->
            <div class="flex items-center justify-between">
                <h2 class="text-xl font-semibold">Edit Wordlist</h2>
                <Button
                    @click="closeModal"
                    variant="ghost"
                    size="sm"
                    class="h-6 w-6 p-0"
                >
                    <X class="h-4 w-4" />
                </Button>
            </div>

            <!-- Form -->
            <div class="space-y-4">
                <!-- Name -->
                <div class="space-y-2">
                    <Label class="text-sm font-medium">
                        Name <span class="text-destructive">*</span>
                    </Label>
                    <Input
                        v-model="form.name"
                        placeholder="Wordlist name..."
                        class="w-full"
                        :class="{ 'border-destructive': errors.name }"
                    />
                    <div class="flex items-center justify-between">
                        <p v-if="errors.name" class="text-xs text-destructive">
                            {{ errors.name }}
                        </p>
                        <span v-else />
                        <span
                            class="text-xs"
                            :class="
                                form.name.trim().length > 100
                                    ? 'text-destructive'
                                    : 'text-muted-foreground'
                            "
                        >
                            {{ form.name.trim().length }}/100
                        </span>
                    </div>
                </div>

                <!-- Description -->
                <div class="space-y-2">
                    <Label class="text-sm font-medium">Description</Label>
                    <Textarea
                        v-model="form.description"
                        placeholder="Brief description of this wordlist..."
                        class="w-full resize-none"
                        rows="3"
                    />
                </div>

                <!-- Tags -->
                <div class="space-y-2">
                    <Label class="text-sm font-medium">Tags</Label>
                    <div class="space-y-2">
                        <Input
                            v-model="newTag"
                            placeholder="Add a tag..."
                            class="w-full"
                            :class="{ 'border-destructive': errors.tag }"
                            @keydown.enter.prevent="addTag"
                        />
                        <p v-if="errors.tag" class="text-xs text-destructive">
                            {{ errors.tag }}
                        </p>
                        <div
                            v-if="form.tags.length > 0"
                            class="flex flex-wrap gap-1"
                        >
                            <span
                                v-for="tag in form.tags"
                                :key="tag"
                                class="inline-flex items-center gap-1 rounded-full bg-muted px-2 py-1 text-xs"
                            >
                                {{ tag }}
                                <button
                                    @click="removeTag(tag)"
                                    class="hover:text-destructive"
                                >
                                    <X class="h-3 w-3" />
                                </button>
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Public -->
                <div class="flex items-center gap-2">
                    <input
                        id="is-public"
                        v-model="form.is_public"
                        type="checkbox"
                        class="h-4 w-4 rounded-full border-border"
                    />
                    <Label for="is-public" class="text-sm font-medium">
                        Public wordlist
                    </Label>
                </div>
            </div>

            <!-- Error Display -->
            <div
                v-if="error"
                class="rounded-md border border-destructive/20 bg-destructive/10 p-3"
            >
                <p class="text-sm text-destructive">{{ error }}</p>
            </div>

            <!-- Loading State -->
            <div v-if="isSaving" class="space-y-2">
                <div class="flex items-center gap-2">
                    <div
                        class="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent"
                    ></div>
                    <span class="text-sm">Saving changes...</span>
                </div>
            </div>

            <!-- Actions -->
            <div class="flex justify-end gap-2 border-t pt-4">
                <Button
                    variant="outline"
                    @click="closeModal"
                    :disabled="isSaving"
                >
                    Cancel
                </Button>
                <Button
                    @click="handleSave"
                    :disabled="!canSave || isSaving"
                    class="min-w-[100px]"
                >
                    <span v-if="isSaving">Saving...</span>
                    <span v-else>Save Changes</span>
                </Button>
            </div>
        </div>
    </Modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import { X } from 'lucide-vue-next';
import { Modal } from '@/components/custom';
import { Button, Input, Textarea, Label, useToast } from '@mkbabb/glass-ui';
import { wordlistApi } from '@/api';
import { logger } from '@/utils/logger';
import type { WordList } from '@/types';

interface Props {
    modelValue: boolean;
    wordlist: WordList;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    'update:modelValue': [value: boolean];
    updated: [wordlist: any];
}>();

const { toast } = useToast();

// Component state
const form = ref({
    name: '',
    description: '',
    tags: [] as string[],
    is_public: false,
});

const newTag = ref('');
const isSaving = ref(false);
const error = ref('');

const errors = ref({
    name: '',
    tag: '',
});

// Computed properties
const modelValue = computed({
    get: () => props.modelValue,
    set: (value) => emit('update:modelValue', value),
});

const canSave = computed(() => {
    const trimmedLen = form.value.name.trim().length;
    return trimmedLen >= 2 && trimmedLen <= 100 && !isSaving.value;
});

// Methods
const closeModal = () => {
    modelValue.value = false;
};

const populateForm = () => {
    form.value = {
        name: props.wordlist.name ?? '',
        description: props.wordlist.description ?? '',
        tags: [...(props.wordlist.tags ?? [])],
        is_public: props.wordlist.is_public ?? false,
    };
    newTag.value = '';
    error.value = '';
    errors.value = { name: '', tag: '' };
};

const addTag = () => {
    errors.value.tag = '';
    const tag = newTag.value.trim().toLowerCase();

    if (!tag) return;

    if (form.value.tags.length >= 10) {
        errors.value.tag = 'Maximum of 10 tags allowed';
        return;
    }

    if (tag.length > 30) {
        errors.value.tag = 'Tag must be 30 characters or fewer';
        return;
    }

    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(tag)) {
        errors.value.tag =
            'Tags may only contain letters, numbers, and hyphens';
        return;
    }

    if (form.value.tags.includes(tag)) {
        errors.value.tag = 'Tag already added';
        return;
    }

    form.value.tags.push(tag);
    newTag.value = '';
};

const removeTag = (tagToRemove: string) => {
    form.value.tags = form.value.tags.filter((tag) => tag !== tagToRemove);
};

const validateForm = (): boolean => {
    errors.value = { name: '', tag: '' };

    if (!form.value.name.trim()) {
        errors.value.name = 'Name is required';
        return false;
    }

    if (form.value.name.trim().length < 2) {
        errors.value.name = 'Name must be at least 2 characters';
        return false;
    }

    if (form.value.name.trim().length > 100) {
        errors.value.name = 'Name must be 100 characters or fewer';
        return false;
    }

    return true;
};

const handleSave = async () => {
    if (!validateForm()) return;

    isSaving.value = true;
    error.value = '';

    try {
        const result = await wordlistApi.updateWordlist(props.wordlist.id, {
            name: form.value.name.trim(),
            description: form.value.description.trim(),
            tags: form.value.tags,
            is_public: form.value.is_public,
        });

        toast({
            title: 'Success',
            description: `Wordlist "${form.value.name}" updated successfully`,
        });

        if (result?.data) {
            emit('updated', result.data);
            closeModal();
        } else {
            error.value = 'Failed to update wordlist. Please try again.';
        }
    } catch (err) {
        logger.error('Update wordlist error:', err);
        error.value = 'Failed to update wordlist. Please try again.';
    } finally {
        isSaving.value = false;
    }
};

// Populate form when modal opens
watch(
    () => props.modelValue,
    (isOpen) => {
        if (isOpen) {
            populateForm();
        }
    }
);

// Clear tag error when user edits the tag input
watch(newTag, () => {
    if (errors.value.tag) {
        errors.value.tag = '';
    }
});
</script>
