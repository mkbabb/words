import { ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { useDebounceFn } from '@vueuse/core';
import type { WordListItem, WordList } from '@/types';
import { wordlistApi } from '@/api';
import { useToast } from '@mkbabb/glass-ui';
import { useWordlistMode } from '@/stores/search/modes/wordlist';
import { useSearchBarStore } from '@/stores/search/search-bar';
import { useWordlistSearch } from '@/components/custom/search/composables/useWordlistSearch';
import { logger } from '@/utils/logger';

/**
 * Manages all data fetching, mutations, and loading state for the word list.
 *
 * Extracted from WordListView so the parent component only wires composables
 * together without touching API calls or store mutations directly.
 */
export function useWordListData() {
    const { searchBar } = useStores();
    const wordlistMode = useWordlistMode();
    const searchBarStore = useSearchBarStore();
    const router = useRouter();
    const wordlistSearch = useWordlistSearch();
    const { toast } = useToast();

    // Loading / lifecycle state
    const isLoadingMeta = ref(false);
    const isLoadingWords = ref(false);
    const hasEverLoaded = ref(false);
    const isChangingWordlist = ref(false);
    const currentPage = ref(0);

    // Data
    const currentWordlistData = ref<WordList | null>(null);
    const preloadedDueCount = ref<number | null>(null);

    // -----------------------------------------------------------------------
    // Data loading
    // -----------------------------------------------------------------------

    const loadWordlistMeta = async (id: string) => {
        if (!id) return;

        isLoadingMeta.value = true;
        try {
            const [response, stats] = await Promise.all([
                wordlistApi.getWordlist(id),
                wordlistApi.getStatistics(id).catch(() => null),
            ]);

            currentWordlistData.value = {
                id: (response.data as any)._id || response.data.id,
                name: response.data.name,
                description: response.data.description,
                hash_id: response.data.hash_id,
                words: [],
                total_words: response.data.total_words,
                unique_words: response.data.unique_words,
                learning_stats: response.data.learning_stats,
                last_accessed: response.data.last_accessed,
                created_at: response.data.created_at,
                updated_at: response.data.updated_at,
                metadata: response.data.metadata || {},
                tags: response.data.tags || [],
                is_public: response.data.is_public || false,
                owner_id: response.data.owner_id,
            };

            const statsData = (stats as any)?.data ?? stats;
            preloadedDueCount.value = statsData?.word_counts?.due_for_review ?? 0;
        } catch (error) {
            logger.error('Failed to load wordlist metadata:', error);
            wordlistMode.setWordlist(null);
        } finally {
            isLoadingMeta.value = false;
        }
    };

    const triggerWordlistSearch = async () => {
        if (!wordlistMode.selectedWordlist) return;

        const wordlistId = wordlistMode.selectedWordlist;
        const query = searchBar.searchQuery.trim();
        wordlistMode.setCurrentQuery(query);

        isLoadingWords.value = true;
        try {
            if (!query) {
                await wordlistSearch.executeWordlistFetch(wordlistId);
                searchBar.hideDropdown();
            } else {
                const results = await wordlistSearch.executeWordlistSearchApi(
                    wordlistId,
                    query,
                );
                if (results.length > 0) {
                    searchBar.openDropdown();
                    searchBar.setSelectedIndex(0);
                } else {
                    searchBar.hideDropdown();
                }
            }
            hasEverLoaded.value = true;
        } catch (error) {
            logger.error('Wordlist search error:', error);
            wordlistMode.clearResults();
            searchBar.hideDropdown();
        } finally {
            isLoadingWords.value = false;
        }
    };

    const loadMoreWords = async () => {
        isLoadingWords.value = true;
        try {
            await wordlistSearch.loadMoreWordlist();
        } catch (error) {
            logger.error('Failed to load more words:', error);
        } finally {
            isLoadingWords.value = false;
        }
    };

    const handleLoadBefore = (offset: number) => {
        wordlistSearch.loadBeforeWordlist(offset);
    };

    // -----------------------------------------------------------------------
    // Mutations
    // -----------------------------------------------------------------------

    const handleWordsUploaded = async (_words: string[]) => {
        if (wordlistMode.selectedWordlist) {
            await loadWordlistMeta(wordlistMode.selectedWordlist);
            await triggerWordlistSearch();
            toast({ title: 'Words uploaded', description: 'Your wordlist has been updated.' });
        }
    };

    const handleReviewSessionComplete = async () => {
        if (wordlistMode.selectedWordlist) {
            await loadWordlistMeta(wordlistMode.selectedWordlist);
            await triggerWordlistSearch();
        }
    };

    const handleRemove = async (word: WordListItem) => {
        const id = currentWordlistData.value?.id;
        if (!id) return;
        try {
            await wordlistApi.removeWord(id, word.word);
            const updated = [...wordlistMode.results].filter((w: any) => w.word !== word.word);
            wordlistMode.setResults(updated as any);
            toast({ title: 'Word removed', description: `"${word.word}" removed from list.` });
        } catch (error) {
            logger.error('Failed to remove word:', error);
        }
    };

    const handleDeleteWordlist = async () => {
        const id = currentWordlistData.value?.id;
        if (!id) return;
        const wordlistName = currentWordlistData.value!.name;

        try {
            await wordlistApi.deleteWordlist(id);
            wordlistMode.setWordlist(null);
            currentWordlistData.value = null;
            router.push({ name: 'Home' });
            toast({ title: 'Wordlist deleted', description: `"${wordlistName}" was deleted.` });
        } catch (error) {
            logger.error('Failed to delete wordlist:', error);
            toast({ title: 'Error', description: 'Failed to delete wordlist.', variant: 'destructive' });
        }
    };

    const updateWordNotes = async (word: WordListItem, newNotes: string) => {
        try {
            const id = currentWordlistData.value?.id;
            if (!id) {
                logger.error('No wordlist selected');
                return;
            }

            await wordlistApi.updateWord(id, word.word, { notes: newNotes });

            const storeResults = [...wordlistMode.results] as WordListItem[];
            const wordIndex = storeResults.findIndex((w) => w.word === word.word);
            if (wordIndex >= 0) {
                storeResults[wordIndex] = { ...storeResults[wordIndex], notes: newNotes } as any;
                wordlistMode.setResults(storeResults);
            }

            toast({ title: 'Notes updated', description: `Notes for "${word.word}" saved.` });
        } catch (error) {
            logger.error('Failed to update notes:', error);
            toast({ title: 'Error', description: 'Failed to update notes. Please try again.', variant: 'destructive' });
        }
    };

    const handleWordlistCreated = async (wordlist: any) => {
        wordlistMode.setWordlist(wordlist.id);
        searchBarStore.setMode('wordlist');
    };

    const handleWordLookup = async (word: string) => {
        await searchBarStore.setMode('lookup');
        searchBarStore.setQuery(word);
        router.push({ name: 'Definition', params: { word } });
    };

    // -----------------------------------------------------------------------
    // Watches — wordlist change + search query + mode switches
    // -----------------------------------------------------------------------

    // Provide a resetCacheCallback so the parent can wire the cache composable
    let _onWordlistChange: (() => void) | null = null;
    const onWordlistChange = (cb: () => void) => { _onWordlistChange = cb; };

    watch(
        () => wordlistMode.selectedWordlist,
        async (newId) => {
            if (newId) {
                isChangingWordlist.value = true;
                hasEverLoaded.value = false;
                currentPage.value = 0;
                wordlistMode.clearResults();
                _onWordlistChange?.();
                await loadWordlistMeta(newId);
                await triggerWordlistSearch();
                isChangingWordlist.value = false;
            } else {
                currentWordlistData.value = null;
            }
        },
        { immediate: true },
    );

    watch(
        () => searchBarStore.searchMode,
        (mode, previousMode) => {
            if (mode === 'wordlist' && wordlistMode.selectedWordlist) {
                triggerWordlistSearch();
            } else if (previousMode === 'wordlist' && mode !== 'wordlist') {
                searchBar.hideDropdown();
            }
        },
    );

    watch(
        () => wordlistMode.searchMode,
        () => {
            if (searchBarStore.searchMode === 'wordlist' && wordlistMode.selectedWordlist) {
                triggerWordlistSearch();
            }
        },
    );

    // Debounced API search for search-query changes
    const debouncedApiSearch = useDebounceFn(async () => {
        if (isChangingWordlist.value || searchBarStore.searchMode !== 'wordlist' || !wordlistMode.selectedWordlist) {
            return;
        }
        await triggerWordlistSearch();
    }, 300);

    watch(
        () => searchBar.searchQuery,
        (newQuery, oldQuery) => {
            if (isChangingWordlist.value || searchBarStore.searchMode !== 'wordlist' || !wordlistMode.selectedWordlist) {
                return;
            }

            const trimmed = newQuery.trim();

            if (!trimmed) {
                searchBar.hideDropdown();
                if (oldQuery?.trim()) {
                    triggerWordlistSearch();
                }
                return;
            }

            debouncedApiSearch();
        },
    );

    return {
        // Loading state
        isLoadingMeta,
        isLoadingWords,
        hasEverLoaded,
        isChangingWordlist,

        // Data
        currentWordlistData,
        preloadedDueCount,

        // Data loading
        loadWordlistMeta,
        triggerWordlistSearch,
        loadMoreWords,
        handleLoadBefore,

        // Mutations
        handleWordsUploaded,
        handleReviewSessionComplete,
        handleRemove,
        handleDeleteWordlist,
        updateWordNotes,
        handleWordlistCreated,
        handleWordLookup,

        // Wiring callback
        onWordlistChange,
    };
}
