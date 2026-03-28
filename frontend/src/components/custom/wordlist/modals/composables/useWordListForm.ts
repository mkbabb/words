import { ref, computed, watch, type Ref } from 'vue';
import { wordlistApi } from '@/api';
import { useSlugGeneration } from '@/composables/useSlugGeneration';
import { useToast } from '@mkbabb/glass-ui';
import { logger } from '@/utils/logger';
import type { WordList } from '@/types';

export interface UseWordListFormOptions {
    modelValue: Ref<boolean>;
    onCreated: (wordlist: WordList) => void;
    onClose: () => void;
}

/**
 * Form logic for the Create Wordlist modal.
 *
 * Manages form state, validation, slug generation, tag management,
 * word parsing, and the create-wordlist API call.
 */
export function useWordListForm(options: UseWordListFormOptions) {
    const { modelValue, onCreated, onClose } = options;

    const { isGenerating: slugGenerating, generateSlugWithFallback } = useSlugGeneration();
    const { toast } = useToast();

    // Form state
    const form = ref({
        name: '',
        description: '',
        tags: [] as string[],
    });

    const initialWordsText = ref('');
    const newTag = ref('');
    const showAllWords = ref(false);
    const isCreating = ref(false);
    const error = ref('');
    const isSlugGenerated = ref(false);

    const errors = ref({
        name: '',
        tag: '',
    });

    // -----------------------------------------------------------------------
    // Computeds
    // -----------------------------------------------------------------------

    const parsedWords = computed(() => {
        if (!initialWordsText.value.trim()) return [];
        return initialWordsText.value
            .split(/[,;\t\n]/)
            .map((word) => word.trim())
            .filter((word) => word && word.length > 0)
            .filter((word, index, arr) => arr.indexOf(word) === index);
    });

    const displayedWords = computed(() => {
        return showAllWords.value ? parsedWords.value : parsedWords.value.slice(0, 10);
    });

    const canCreate = computed(() => {
        const trimmedLen = form.value.name.trim().length;
        return trimmedLen >= 2 && trimmedLen <= 100 && !isCreating.value;
    });

    // -----------------------------------------------------------------------
    // Methods
    // -----------------------------------------------------------------------

    const resetForm = () => {
        form.value = { name: '', description: '', tags: [] };
        initialWordsText.value = '';
        newTag.value = '';
        showAllWords.value = false;
        error.value = '';
        errors.value = { name: '', tag: '' };
        isSlugGenerated.value = false;
    };

    const closeModal = () => {
        onClose();
        resetForm();
    };

    const generateSlugName = async () => {
        const slugName = await generateSlugWithFallback();
        if (slugName) {
            form.value.name = slugName;
            isSlugGenerated.value = true;
        }
    };

    const handleNameInput = () => {
        if (isSlugGenerated.value) {
            isSlugGenerated.value = false;
        }
        const trimmed = form.value.name.trim();
        if (trimmed.length > 0 && trimmed.length < 2) {
            errors.value.name = 'Name must be at least 2 characters';
        } else if (trimmed.length > 100) {
            errors.value.name = 'Name must be 100 characters or fewer';
        } else {
            errors.value.name = '';
        }
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
            errors.value.tag = 'Tags may only contain letters, numbers, and hyphens';
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

    const handleCreate = async () => {
        if (!validateForm()) return;

        isCreating.value = true;
        error.value = '';

        try {
            const wordlist = await wordlistApi.createWordlist({
                name: form.value.name.trim(),
                description: form.value.description.trim() || '',
                words: parsedWords.value,
            });

            toast({
                title: 'Success',
                description: `Wordlist "${form.value.name}" created successfully`,
            });

            if (wordlist?.data) {
                onCreated(wordlist.data);
                closeModal();
            } else {
                error.value = 'Failed to create wordlist. Please try again.';
            }
        } catch (err) {
            logger.error('Create wordlist error:', err);
            error.value = 'Failed to create wordlist. Please try again.';
        } finally {
            isCreating.value = false;
        }
    };

    // -----------------------------------------------------------------------
    // Watches
    // -----------------------------------------------------------------------

    watch(() => form.value.name, () => {
        handleNameInput();
    });

    watch(newTag, () => {
        if (errors.value.tag) {
            errors.value.tag = '';
        }
    });

    watch(modelValue, async (isOpen) => {
        if (isOpen && !form.value.name.trim()) {
            await generateSlugName();
        }
    });

    return {
        // State
        form,
        initialWordsText,
        newTag,
        showAllWords,
        isCreating,
        error,
        errors,
        isSlugGenerated,
        slugGenerating,

        // Computeds
        parsedWords,
        displayedWords,
        canCreate,

        // Methods
        resetForm,
        closeModal,
        generateSlugName,
        handleNameInput,
        addTag,
        removeTag,
        validateForm,
        handleCreate,
    };
}
