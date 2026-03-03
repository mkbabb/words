import { ref, watch, type Ref, type ComputedRef } from 'vue';
import { useMagicKeys, whenever } from '@vueuse/core';
import { useContentStore, useNotificationStore } from '@/stores';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useRouterSync } from '@/stores/composables/useRouterSync';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';
import { lookupApi } from '@/api/lookup';
import { logger } from '@/utils/logger';
import type { ImageMedia } from '@/types/api';

interface UseDefinitionActionsOptions {
    entry: ComputedRef<any>;
    editModeEnabled: Ref<boolean>;
}

/**
 * Encapsulates all event handlers and keyboard shortcuts for DefinitionDisplay.
 */
export function useDefinitionActions(options: UseDefinitionActionsOptions) {
    const { entry, editModeEnabled } = options;

    const contentStore = useContentStore();
    const notificationStore = useNotificationStore();
    const searchBar = useSearchBarStore();

    const orchestrator = useSearchOrchestrator({
        query: ref(searchBar.searchQuery),
    });

    // Modal state
    const showWordlistModal = ref(false);
    const wordToAdd = ref('');
    const showThemeDropdown = ref(false);
    const showVersionHistory = ref(false);
    const isResynthesizing = ref(false);

    // Event handlers
    const handleRegenerateExamples = async (definitionIndex: number) => {
        try {
            await contentStore.regenerateExamples(definitionIndex);
        } catch (error) {
            logger.error('Failed to regenerate examples:', error);
        }
    };

    const handleImagesUpdated = async (_newImages: ImageMedia[]) => {
        try {
            await contentStore.refreshEntryImages();
        } catch (error) {
            logger.error('Failed to refresh entry images:', error);
            notificationStore.showNotification({
                type: 'warning',
                message:
                    'Images uploaded but display may not be current. Try refreshing.',
                duration: 5000,
            });
        }
    };

    const handleImageDeleted = async (_imageId: string) => {
        try {
            await contentStore.refreshEntryImages();

            notificationStore.showNotification({
                type: 'success',
                message: 'Image deleted successfully',
                duration: 3000,
            });
        } catch (error) {
            logger.error(
                'Failed to refresh entry after image deletion:',
                error
            );
            notificationStore.showNotification({
                type: 'error',
                message:
                    'Image deleted but display may not be current. Try refreshing.',
                duration: 5000,
            });
        }
    };

    const handleClusterNameUpdate = async (
        clusterId: string,
        newName: string
    ) => {
        const definition = entry.value?.definitions?.find(
            (def: any) =>
                def.meaning_cluster?.id === clusterId ||
                def.meaning_cluster?.name === clusterId
        );

        if (definition?.id) {
            await contentStore.updateDefinition(definition.id, {
                meaning_cluster: {
                    ...definition.meaning_cluster,
                    name: newName,
                } as any,
            });
        }
    };

    const handleWordSearch = (word: string) => {
        const { navigateToLookupMode } = useRouterSync();
        navigateToLookupMode(word, 'dictionary');
    };

    const handleAddToWordlist = (word: string) => {
        wordToAdd.value = word;
        showWordlistModal.value = true;
    };

    const handleWordAddedToList = (_wordlistName: string) => {
        const word = wordToAdd.value;
        const notifications = useNotificationStore();
        notifications.showNotification({
            type: 'success',
            message: `"${word}" added to wordlist`,
        });
    };

    const handleRetryLookup = () => {
        if (contentStore.definitionError?.originalWord) {
            const wordToRetry = contentStore.definitionError.originalWord;
            contentStore.clearError();
            handleWordSearch(wordToRetry);
        }
    };

    const handleShowHelp = () => {
        // TODO: Implement help system
    };

    const handleSuggestAlternatives = () => {
        searchBar.setSubMode('lookup', 'suggestions');
    };

    const handleRetryThesaurus = async () => {
        if (entry.value?.word) {
            try {
                await orchestrator.getThesaurusData(entry.value.word);
            } catch (error) {
                logger.error('Failed to retry thesaurus lookup:', error);
                notificationStore.showNotification({
                    type: 'error',
                    message: 'Failed to load thesaurus data. Please try again.',
                    duration: 3000,
                });
            }
        }
    };

    // Re-synthesize word (admin only)
    const handleReSynthesize = async () => {
        const word = entry.value?.word;
        if (!word) return;

        isResynthesizing.value = true;
        try {
            const newEntry = await lookupApi.reSynthesize(word);
            contentStore.setCurrentEntry(newEntry);
            notificationStore.showNotification({
                type: 'success',
                message: `"${word}" re-synthesized with ${newEntry.definitions?.length || 0} definitions.`,
                duration: 4000,
            });
        } catch (error) {
            logger.error('Re-synthesis failed:', error);
            notificationStore.showNotification({
                type: 'error',
                message: 'Re-synthesis failed. Please try again.',
                duration: 4000,
            });
        } finally {
            isResynthesizing.value = false;
        }
    };

    // Toggle version history panel
    const handleToggleVersionHistory = () => {
        showVersionHistory.value = !showVersionHistory.value;
    };

    // Save all changes function
    const saveAllChanges = () => {
        document.dispatchEvent(new CustomEvent('save-all-edits'));
    };

    // Keyboard shortcuts using VueUse magic keys
    const keys = useMagicKeys();

    // Toggle edit mode with Cmd/Ctrl + E
    whenever(keys.cmd_e, () => {
        editModeEnabled.value = !editModeEnabled.value;
    });
    whenever(keys.ctrl_e, () => {
        editModeEnabled.value = !editModeEnabled.value;
    });

    // Exit edit mode with Escape
    whenever(keys.escape, () => {
        if (editModeEnabled.value) {
            editModeEnabled.value = false;
            saveAllChanges();
        }
    });

    // Navigation with arrow keys
    whenever(keys.arrowdown, () => {
        if (entry.value?.definitions) {
            document.dispatchEvent(
                new CustomEvent('navigate-definition', {
                    detail: { direction: 'next' },
                })
            );
        }
    });
    whenever(keys.arrowup, () => {
        if (entry.value?.definitions) {
            document.dispatchEvent(
                new CustomEvent('navigate-definition', {
                    detail: { direction: 'prev' },
                })
            );
        }
    });

    // Watch edit mode changes to save
    watch(editModeEnabled, (newVal, oldVal) => {
        if (oldVal && !newVal) {
            saveAllChanges();
        }
    });

    // Watch mode changes to ensure thesaurus data is loaded
    watch(
        () => searchBar.getSubMode('lookup'),
        async (newMode) => {
            if (newMode === 'thesaurus' && entry.value) {
                await orchestrator.getThesaurusData(entry.value.word);
            }
        }
    );

    return {
        // State
        showWordlistModal,
        wordToAdd,
        showThemeDropdown,
        showVersionHistory,
        isResynthesizing,

        // Methods
        handleRegenerateExamples,
        handleImagesUpdated,
        handleImageDeleted,
        handleClusterNameUpdate,
        handleWordSearch,
        handleAddToWordlist,
        handleWordAddedToList,
        handleRetryLookup,
        handleShowHelp,
        handleSuggestAlternatives,
        handleRetryThesaurus,
        handleReSynthesize,
        handleToggleVersionHistory,
        saveAllChanges,
    };
}
