import { wordlistApi } from '@/api'
import { useWordlistMode } from '@/stores/search/modes/wordlist'
import type { WordList } from '@/types'

const CACHE_TTL_MS = 5 * 60 * 1000 // 5 minutes
let lastFetchTime = 0

/**
 * Manages wordlist data fetching with 5-minute TTL cache.
 * Extracts API calls from the wordlist mode store.
 */
export function useWordlistData() {
  const wordlistMode = useWordlistMode()

  async function fetchAllWordlists(force = false): Promise<void> {
    if (wordlistMode.wordlistsLoading) return

    // Skip refetch if data is fresh and already populated
    if (
      !force &&
      wordlistMode.allWordlists.length > 0 &&
      Date.now() - lastFetchTime < CACHE_TTL_MS
    ) {
      return
    }

    wordlistMode.setWordlistsLoading(true)
    try {
      const response = await wordlistApi.getWordlists({ limit: 50 })
      const wordlists: WordList[] = response.items.map((wl: any) => ({
        id: wl._id || wl.id,
        name: wl.name,
        description: wl.description,
        hash_id: wl.hash_id,
        words: wl.words || [],
        total_words: wl.total_words,
        unique_words: wl.unique_words,
        learning_stats: wl.learning_stats,
        last_accessed: wl.last_accessed,
        created_at: wl.created_at,
        updated_at: wl.updated_at,
        metadata: wl.metadata || {},
        tags: wl.tags || [],
        is_public: wl.is_public || false,
        owner_id: wl.owner_id,
      }))
      wordlistMode.setAllWordlists(wordlists)
      lastFetchTime = Date.now()
    } catch {
      // Silently degrade
    } finally {
      wordlistMode.setWordlistsLoading(false)
    }
  }

  /** Invalidate cache so next fetchAllWordlists() re-fetches. */
  function invalidateCache() {
    lastFetchTime = 0
  }

  return { fetchAllWordlists, invalidateCache }
}
