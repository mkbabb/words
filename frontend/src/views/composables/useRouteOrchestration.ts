import { computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useStores } from '@/stores';
import { useSearchOrchestrator } from '@/components/custom/search/composables/useSearchOrchestrator';

/**
 * Route-driven orchestration for Home view.
 *
 * Watches route changes and coordinates stores, API calls, and navigation.
 * Owns the orchestrator instance and the mode-change cleanup watcher.
 */
export function useRouteOrchestration() {
    const { searchBar, content, loading } = useStores();
    const route = useRoute();
    const router = useRouter();

    const orchestrator = useSearchOrchestrator({
        query: computed(() => searchBar.searchQuery),
    });

    // ── Route handler ────────────────────────────────────────────────

    watch(
        () => route.fullPath,
        async () => {
            const routeName = route.name;

            if (routeName === 'Definition' && route.params.word) {
                await handleDefinitionRoute(route.params.word as string);
            } else if (routeName === 'Thesaurus' && route.params.word) {
                await handleThesaurusRoute(route.params.word as string);
            } else if (routeName === 'Search' && route.params.query) {
                await handleSearchRoute(route.params.query as string);
            } else if (routeName === 'Wordlist' && route.params.wordlistId) {
                handleWordlistRoute(route.params.wordlistId as string);
            } else if (routeName === 'WordlistSearch' && route.params.wordlistId) {
                handleWordlistSearchRoute(
                    route.params.wordlistId as string,
                    (route.params.query as string) || '',
                );
            } else if (routeName === 'Home') {
                handleHomeRoute();
            }
        },
        { immediate: true },
    );

    // Clear content when leaving lookup mode
    watch(
        () => searchBar.searchMode,
        (newMode, oldMode) => {
            if (newMode !== oldMode && newMode !== 'lookup') {
                content.clearCurrentEntry();
            }
        },
    );

    // ── Route handlers ───────────────────────────────────────────────

    async function handleDefinitionRoute(word: string) {
        searchBar.setMode('lookup');
        searchBar.setSubMode('lookup', 'dictionary');
        searchBar.setQuery(word);
        searchBar.hideControls();
        searchBar.hideDropdown();

        if (!content.currentEntry || content.currentEntry.word !== word) {
            content.clearCurrentEntry();
            try {
                const definition = await orchestrator.getDefinition(word, {
                    onProgress: (stage, progress) => {
                        loading.setLoadingStage(stage);
                        loading.setLoadingProgress(progress);
                    },
                });
                if (definition) {
                    content.setCurrentEntry(definition);
                    searchBar.hideControls();
                    searchBar.hideDropdown();
                }
            } catch (error: any) {
                if (isAbortError(error)) return;
                content.setError({
                    hasError: true,
                    errorType: 'unknown',
                    errorMessage: error?.message || 'Failed to look up word',
                    canRetry: true,
                    originalWord: word,
                });
            }
        }
    }

    async function handleThesaurusRoute(word: string) {
        searchBar.setMode('lookup');
        searchBar.setSubMode('lookup', 'thesaurus');
        searchBar.setQuery(word);
        searchBar.hideControls();
        searchBar.hideDropdown();

        // Ensure we have the definition entry first
        if (!content.currentEntry || content.currentEntry.word !== word) {
            try {
                const definition = await orchestrator.getDefinition(word, {
                    onProgress: (stage, progress) => {
                        loading.setLoadingStage(stage);
                        loading.setLoadingProgress(progress);
                    },
                });
                if (definition) {
                    content.setCurrentEntry(definition);
                }
            } catch (error: any) {
                if (isAbortError(error)) return;
                searchBar.setSubMode('lookup', 'dictionary');
                router.replace({ name: 'Definition', params: { word } });
                return;
            }
        }

        // Fetch thesaurus data
        const hasThesaurus =
            content.currentThesaurus && content.currentThesaurus.word === word;
        if (!hasThesaurus) {
            try {
                const data = await orchestrator.getThesaurusData(word);
                if (data) {
                    content.setCurrentThesaurus(data);
                    searchBar.hideControls();
                    searchBar.hideDropdown();
                }
            } catch (error: any) {
                if (isAbortError(error)) return;
                content.setError({
                    hasError: true,
                    errorType: 'unknown',
                    errorMessage:
                        error?.message || 'Failed to load thesaurus data',
                    canRetry: true,
                    originalWord: word,
                });
            }
        }
    }

    async function handleSearchRoute(query: string) {
        searchBar.setMode('lookup');
        searchBar.setQuery(query);
        await orchestrator.performSearch();
    }

    function handleWordlistRoute(wordlistId: string) {
        searchBar.clearQuery();
        content.clearCurrentEntry();
        searchBar.setMode('wordlist');
        const { wordlistMode } = useStores();
        wordlistMode.setWordlist(wordlistId);
    }

    function handleWordlistSearchRoute(wordlistId: string, query: string) {
        content.clearCurrentEntry();
        searchBar.setMode('wordlist');
        const { wordlistMode } = useStores();
        wordlistMode.setWordlist(wordlistId);
        if (query) {
            searchBar.setQuery(query);
        } else {
            searchBar.clearQuery();
        }
    }

    function handleHomeRoute() {
        searchBar.clearQuery();
        content.clearCurrentEntry();
        if (searchBar.searchMode === 'wordlist') {
            const { wordlistMode } = useStores();
            if (wordlistMode.selectedWordlist) {
                router.replace({
                    name: 'Wordlist',
                    params: { wordlistId: wordlistMode.selectedWordlist },
                });
            }
        }
    }

    // ── Helpers ───────────────────────────────────────────────────────

    function isAbortError(error: any): boolean {
        const message = error?.message || '';
        return message.includes('aborted') || error?.name === 'AbortError';
    }

    return { orchestrator };
}
