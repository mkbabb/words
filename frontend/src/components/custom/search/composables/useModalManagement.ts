import { ref, nextTick } from 'vue';

/**
 * Manages expand modal state and operations
 * Handles modal visibility and query submission
 */
export function useModalManagement() {
  const showExpandModal = ref(false);
  const expandedQuery = ref('');

  /**
   * Open the expand modal
   */
  const handleExpandClick = () => {
    showExpandModal.value = true;
  };

  /**
   * Close the expand modal
   */
  const closeExpandModal = () => {
    showExpandModal.value = false;
    expandedQuery.value = '';
  };

  /**
   * Submit the expanded query
   */
  const submitExpandedQuery = async (query: string, onSubmit: () => Promise<void>) => {
    expandedQuery.value = query;
    showExpandModal.value = false;
    
    await nextTick();
    await onSubmit();
  };

  return {
    // State
    showExpandModal,
    expandedQuery,
    
    // Methods
    handleExpandClick,
    closeExpandModal,
    submitExpandedQuery,
  };
}