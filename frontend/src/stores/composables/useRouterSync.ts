import { useRouter } from 'vue-router'

/**
 * Router synchronization composable
 * Provides navigation helpers for store ↔ URL coordination
 */
export function useRouterSync() {
  const router = useRouter()

  const navigateToLookupMode = (word: string, subMode: string = 'dictionary') => {
    const routeName = subMode === 'thesaurus' ? 'Thesaurus' : 'Definition'
    // Use replace to avoid triggering the route watcher re-fetch
    router.replace({ name: routeName, params: { word } }).catch(() => {
      router.replace({ path: `/definition/${encodeURIComponent(word)}` })
    })
  }

  return {
    navigateToLookupMode
  }
}
