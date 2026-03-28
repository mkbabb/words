import { ref, readonly, computed } from 'vue'
import { suggestionsApi } from '@/api'
import { useAuthStore } from '@/stores/auth'
import { useHistoryStore } from '@/stores/content/history'
import { logger } from '@/utils/logger'
import type { VocabularySuggestion } from '@/types'

// ── Module-level singleton cache ──────────────────────────────────────────
// Shared across all call-sites so there is exactly one TTL-guarded cache.

interface SuggestionsCache {
  suggestions: VocabularySuggestion[]
  lastWord: string | null
  timestamp: number | null
}

const suggestionsCache = ref<SuggestionsCache>({
  suggestions: [],
  lastWord: null,
  timestamp: null,
})

const ONE_HOUR = 60 * 60 * 1000

/**
 * Computed list of valid (non-expired) vocabulary suggestions.
 * Consumers can bind to this reactively.
 */
export const vocabularySuggestions = computed<VocabularySuggestion[]>(() => {
  const cache = suggestionsCache.value
  if (
    cache.suggestions.length > 0 &&
    cache.timestamp &&
    Date.now() - cache.timestamp < ONE_HOUR
  ) {
    return cache.suggestions
  }
  return []
})

// ── Composable ────────────────────────────────────────────────────────────

/**
 * Manages vocabulary suggestion fetching with throttling and caching.
 * The cache is a module-level singleton -- no store dependency needed.
 */
export function useVocabularySuggestions() {
  const isLoading = ref(false)

  async function refreshSuggestions(forceRefresh = false): Promise<void> {
    const auth = useAuthStore()
    if (!auth.isAuthenticated) return

    const historyStore = useHistoryStore()
    const currentWord = historyStore.recentLookupWords[0]
    const cache = suggestionsCache.value

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

      suggestionsCache.value = {
        suggestions: newSuggestions,
        lastWord: currentWord,
        timestamp: Date.now(),
      }
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

  /** Clear the singleton cache (e.g. on logout). */
  function clearSuggestionsCache() {
    suggestionsCache.value = {
      suggestions: [],
      lastWord: null,
      timestamp: null,
    }
  }

  /** Invalidate cache so the next refresh fetches fresh data. */
  function invalidateSuggestionsCache() {
    suggestionsCache.value = { ...suggestionsCache.value, timestamp: null }
  }

  return {
    isLoading: readonly(isLoading),
    vocabularySuggestions,
    refreshSuggestions,
    getHistoryBasedSuggestions,
    clearSuggestionsCache,
    invalidateSuggestionsCache,
  }
}
