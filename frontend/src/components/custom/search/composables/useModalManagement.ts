import { nextTick } from 'vue';
import { useSearchBarUI } from './useSearchBarUI';

/**
 * Manages expand modal state and operations
 * Uses uiState.showExpandModal as the single source of truth
 */
export function useModalManagement() {
  const { uiState } = useSearchBarUI();

  /**
   * Open the expand modal
   */
  const handleExpandClick = () => {
    uiState.showExpandModal = true;
  };

  /**
   * Close the expand modal
   */
  const closeExpandModal = () => {
    uiState.showExpandModal = false;
  };

  /**
   * Submit the expanded query
   */
  const submitExpandedQuery = async (_query: string, onSubmit: () => Promise<void>) => {
    uiState.showExpandModal = false;

    await nextTick();
    await onSubmit();
  };

  return {
    // Methods
    handleExpandClick,
    closeExpandModal,
    submitExpandedQuery,
  };
}
