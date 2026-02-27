import { useRouter } from 'vue-router'

/**
 * Router synchronization composable
 * Provides navigation helpers for store ↔ URL coordination
 */
export function useRouterSync() {
  const router = useRouter()

  const navigateToLookupMode = (word: string, subMode: string = 'dictionary') => {
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition'
    router.push({ name: routeName, params: { word } }).catch(() => {
      // Fallback if named route doesn't exist
      router.push({ path: `/definition/${encodeURIComponent(word)}` })
    })
  }

  return {
    navigateToLookupMode
  }
}
