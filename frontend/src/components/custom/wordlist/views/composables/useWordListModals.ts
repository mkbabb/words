import { ref, watch } from 'vue';
import type { WordListItem } from '@/types';

/**
 * Manages all modal visibility state and the handlers that bridge between modals.
 *
 * Extracted from WordListView to isolate the six modal booleans, selected-word refs,
 * and the functions that open/close modals in response to user actions.
 */
export function useWordListModals() {
    // Modal visibility
    const showUploadModal = ref(false);
    const showCreateModal = ref(false);
    const showEditNotesModal = ref(false);
    const showReviewModal = ref(false);
    const showDetailModal = ref(false);
    const showDeleteDialog = ref(false);

    // Selected / editing word refs
    const selectedWord = ref<WordListItem | null>(null);
    const editingWord = ref<WordListItem | null>(null);
    const reviewSelectedWords = ref<string[] | undefined>(undefined);

    // ---- Handlers ----

    const handleWordClick = (word: WordListItem) => {
        selectedWord.value = word;
        showDetailModal.value = true;
    };

    const handleStartReviewFromDetail = () => {
        showDetailModal.value = false;
        showReviewModal.value = true;
    };

    const handleEdit = (word: WordListItem) => {
        showDetailModal.value = false;
        editingWord.value = word;
        showEditNotesModal.value = true;
    };

    const handleReviewSelected = (selectedWordSet: Set<string> | undefined) => {
        reviewSelectedWords.value = selectedWordSet ? Array.from(selectedWordSet) : undefined;
        showReviewModal.value = true;
    };

    const handleStartFullReview = () => {
        reviewSelectedWords.value = undefined;
        showReviewModal.value = true;
    };

    // Reset selected review words when modal closes
    watch(showReviewModal, (val) => {
        if (!val) reviewSelectedWords.value = undefined;
    });

    return {
        // Visibility refs
        showUploadModal,
        showCreateModal,
        showEditNotesModal,
        showReviewModal,
        showDetailModal,
        showDeleteDialog,

        // Word refs
        selectedWord,
        editingWord,
        reviewSelectedWords,

        // Handlers
        handleWordClick,
        handleStartReviewFromDetail,
        handleEdit,
        handleReviewSelected,
        handleStartFullReview,
    };
}
