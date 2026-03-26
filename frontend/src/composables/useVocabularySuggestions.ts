import { ref, readonly } from 'vue'
import { suggestionsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useHistoryStore } from '@/stores/content/history'
import { logger } from '@/utils/logger'
import type { VocabularySuggestion } from '@/types'

/**
 * Manages vocabulary suggestion fetching with throttling and caching.
 * Extracts API calls from the history store.
 */
export function useVocabularySuggestions() {
  const isLoading = ref(false)

  async function refreshSuggestions(forceRefresh = false): Promise<void> {
    const auth = useAuthStore()
    if (!auth.isAuthenticated) return

    const historyStore = useHistoryStore()
    const ONE_HOUR = 60 * 60 * 1000
    const currentWord = historyStore.recentLookupWords[0]
    const cache = historyStore.suggestionsCache

    if (isLoading.value && !forceRefresh) return

    if (
      !forceRefresh &&
      cache.suggestions.length > 0 &&
      cache.timestamp &&
      Date.now() - cache.timestamp < ONE_HOUR &&
      currentWord === cache.lastWord
    ) {
      return
    }

    isLoading.value = true
    try {
      const recentWords = historyStore.recentLookupWords.slice(0, 10)
      const response = await suggestionsApi.getVocabulary(recentWords)
      const newSuggestions: VocabularySuggestion[] = response.words.map(
        (word: string) => ({
          word,
          reasoning: '',
          difficulty_level: 0,
          semantic_category: '',
        })
      )

      historyStore.setSuggestionsCache({
        suggestions: newSuggestions,
        lastWord: currentWord,
        timestamp: Date.now(),
      })
    } catch (error) {
      logger.error('Failed to get vocabulary suggestions:', error)
    } finally {
      isLoading.value = false
    }
  }

  async function getHistoryBasedSuggestions(): Promise<string[]> {
    const auth = useAuthStore()
    if (!auth.isAuthenticated) return []

    const historyStore = useHistoryStore()
    try {
      const recentWords = historyStore.recentLookupWords.slice(0, 10)
      const response = await suggestionsApi.getVocabulary(recentWords)
      return response.words
    } catch (error) {
      logger.error('Failed to get history-based suggestions:', error)
      return historyStore.recentLookupWords.slice(0, 4)
    }
  }

  return {
    isLoading: readonly(isLoading),
    refreshSuggestions,
    getHistoryBasedSuggestions,
  }
}
